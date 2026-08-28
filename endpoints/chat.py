from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from library.extensions import db
from library.models.chat_message import ChatMessage
from library.models.conversation import Conversation
from library.models.conversation_participant import ConversationParticipant
from library.models.poll import Poll
from library.models.poll_option import PollOption
from library.models.poll_vote import PollVote
from library.models.user import User
from library.services.chat_service import ChatService
from library.services.image_storage import ImageStorage
from library.services.translator import t

bp_chat = Blueprint("chat", __name__)
chat_service = ChatService()

MAX_POLL_OPTIONS = 4
MIN_POLL_OPTIONS = 2


def _serialize_poll(poll: Poll) -> dict:
    return {
        "id": poll.id,
        "question": poll.question,
        "options": [
            {"id": option.id, "text": option.text, "count": len(option.votes)} for option in poll.options
        ],
        "my_vote_option_id": next(
            (option.id for option in poll.options for vote in option.votes if vote.user_id == current_user.id),
            None,
        ),
    }


def _preview_body(message: ChatMessage) -> str:
    if message.message_type == "image":
        return t("chat.preview_image")
    if message.message_type == "location":
        return t("chat.preview_location")
    if message.message_type == "poll":
        return t("chat.preview_poll")
    return message.body[:60]


def _serialize_message(message: ChatMessage) -> dict:
    data = {
        "id": message.id,
        "sender": message.sender.username,
        "sender_avatar": message.sender.display_avatar_url,
        "body": message.body,
        "message_type": message.message_type,
        "is_own": message.sender_id == current_user.id,
        "created_at": message.created_at.strftime("%Y.%m.%d %H:%M"),
    }
    if message.message_type == "image" and message.image:
        data["image_url"] = message.image.url
    elif message.message_type == "location" and message.lat is not None:
        data["lat"] = message.lat
        data["lon"] = message.lon
    elif message.message_type == "poll" and message.poll:
        data["poll"] = _serialize_poll(message.poll)
    elif message.message_type == "tag_added" and message.tag_point:
        data["tag_id"] = message.tag_point.id
        data["tag_photo_url"] = message.tag_point.photo_image.url if message.tag_point.photo_image else None
    return data


def _conversation_display(conversation: Conversation) -> dict:
    last_message = conversation.messages[-1] if conversation.messages else None

    if conversation.kind == "band":
        title = conversation.band.name
        avatar_url = conversation.band.reference_image.url if conversation.band.reference_image else None
    else:
        other = next(
            (p.user for p in conversation.participants if p.user_id != current_user.id),
            None,
        )
        title = other.username if other else "?"
        avatar_url = other.display_avatar_url if other else None

    return {
        "conversation": conversation,
        "title": title,
        "avatar_url": avatar_url,
        "last_message": last_message,
    }


def _inbox_items() -> list:
    conversation_ids = [
        p.conversation_id
        for p in ConversationParticipant.query.filter_by(user_id=current_user.id).all()
    ]
    conversations = Conversation.query.filter(Conversation.id.in_(conversation_ids)).all()
    items = [_conversation_display(c) for c in conversations]
    items.sort(key=lambda item: item["last_message"].created_at if item["last_message"] else item["conversation"].created_at, reverse=True)
    return items


@bp_chat.route("/chat")
@login_required
def inbox():
    return render_template("chat_inbox.html")


@bp_chat.route("/api/chat/inbox")
@login_required
def api_inbox():
    offset = request.args.get("offset", type=int, default=0)
    limit = min(request.args.get("limit", type=int, default=10), 50)
    page = _inbox_items()[offset : offset + limit]

    return jsonify(
        [
            {
                "conversation_id": item["conversation"].id,
                "title": item["title"],
                "avatar_url": item["avatar_url"],
                "is_band": item["conversation"].kind == "band",
                "last_message_sender": item["last_message"].sender.username if item["last_message"] else None,
                "last_message_body": _preview_body(item["last_message"]) if item["last_message"] else None,
            }
            for item in page
        ]
    )


@bp_chat.route("/chat/with/<username>")
@login_required
def start_direct(username: str):
    other = User.query.filter_by(username=username).first()
    if other is None:
        abort(404)
    if other.id == current_user.id:
        abort(400)

    existing = chat_service.find_direct_conversation(current_user, other)
    if existing is None and not other.allow_direct_messages:
        flash(t("flash.cannot_message_user"), "error")
        return redirect(url_for("profile.user_profile", username=other.username))

    conversation = existing or chat_service.get_or_create_direct_conversation(current_user, other)
    return redirect(url_for("chat.conversation_view", conversation_id=conversation.id))


@bp_chat.route("/chat/band/<int:band_id>")
@login_required
def start_band(band_id: int):
    conversation = Conversation.query.filter_by(kind="band", band_id=band_id).first()
    if conversation is None or not chat_service.is_participant(conversation, current_user):
        abort(403)
    return redirect(url_for("chat.conversation_view", conversation_id=conversation.id))


@bp_chat.route("/chat/<int:conversation_id>")
@login_required
def conversation_view(conversation_id: int):
    conversation = Conversation.query.get_or_404(conversation_id)
    if not chat_service.is_participant(conversation, current_user):
        abort(403)

    display = _conversation_display(conversation)
    recent_messages = (
        ChatMessage.query.filter_by(conversation_id=conversation_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
        .all()
    )
    recent_messages.reverse()
    chat_service.mark_read(conversation, current_user)

    return render_template(
        "chat_conversation.html",
        conversation=conversation,
        title=display["title"],
        initial_messages=[_serialize_message(m) for m in recent_messages],
    )


@bp_chat.route("/chat/<int:conversation_id>/send", methods=["POST"])
@login_required
def send_message(conversation_id: int):
    conversation = Conversation.query.get_or_404(conversation_id)
    if not chat_service.is_participant(conversation, current_user):
        abort(403)

    body = request.form.get("body", "").strip()[:2000]
    if body:
        chat_service.post_message(conversation, current_user, body)

    return redirect(url_for("chat.conversation_view", conversation_id=conversation_id))


@bp_chat.route("/chat/<int:conversation_id>/send-image", methods=["POST"])
@login_required
def send_image(conversation_id: int):
    conversation = Conversation.query.get_or_404(conversation_id)
    if not chat_service.is_participant(conversation, current_user):
        abort(403)

    photo = request.files.get("image")
    if photo is None or photo.filename == "":
        return jsonify({"error": "missing_image"}), 400

    storage = ImageStorage(current_app.config["IMAGES_ROOT"])
    try:
        image = storage.save(photo, "chat", uploaded_by_id=current_user.id)
    except ValueError:
        return jsonify({"error": "unsupported_image"}), 400

    message = ChatMessage(
        conversation_id=conversation.id, sender_id=current_user.id, message_type="image", image_id=image.id
    )
    db.session.add(message)
    db.session.commit()
    chat_service.mark_read(conversation, current_user)

    return jsonify(_serialize_message(message))


@bp_chat.route("/chat/<int:conversation_id>/send-location", methods=["POST"])
@login_required
def send_location(conversation_id: int):
    conversation = Conversation.query.get_or_404(conversation_id)
    if not chat_service.is_participant(conversation, current_user):
        abort(403)

    lat = request.form.get("lat", type=float)
    lon = request.form.get("lon", type=float)
    if lat is None or lon is None:
        return jsonify({"error": "missing_location"}), 400

    message = ChatMessage(
        conversation_id=conversation.id, sender_id=current_user.id, message_type="location", lat=lat, lon=lon
    )
    db.session.add(message)
    db.session.commit()
    chat_service.mark_read(conversation, current_user)

    return jsonify(_serialize_message(message))


@bp_chat.route("/chat/<int:conversation_id>/poll", methods=["POST"])
@login_required
def create_poll(conversation_id: int):
    conversation = Conversation.query.get_or_404(conversation_id)
    if not chat_service.is_participant(conversation, current_user):
        abort(403)
    if conversation.kind != "band":
        abort(400)

    question = request.form.get("question", "").strip()[:200]
    options = [opt.strip()[:100] for opt in request.form.getlist("option") if opt.strip()]
    if not question or len(options) < MIN_POLL_OPTIONS:
        return jsonify({"error": "invalid_poll"}), 400
    options = options[:MAX_POLL_OPTIONS]

    message = ChatMessage(conversation_id=conversation.id, sender_id=current_user.id, message_type="poll")
    db.session.add(message)
    db.session.flush()

    poll = Poll(chat_message_id=message.id, question=question)
    db.session.add(poll)
    db.session.flush()

    for option_text in options:
        db.session.add(PollOption(poll_id=poll.id, text=option_text))

    db.session.commit()
    chat_service.mark_read(conversation, current_user)

    return jsonify(_serialize_message(message))


@bp_chat.route("/api/chat/polls/<int:poll_id>")
@login_required
def poll_detail(poll_id: int):
    poll = Poll.query.get_or_404(poll_id)
    if not chat_service.is_participant(poll.chat_message.conversation, current_user):
        abort(403)
    return jsonify(_serialize_poll(poll))


@bp_chat.route("/api/chat/polls/<int:poll_id>/vote", methods=["POST"])
@login_required
def vote_poll(poll_id: int):
    poll = Poll.query.get_or_404(poll_id)
    conversation = poll.chat_message.conversation
    if not chat_service.is_participant(conversation, current_user):
        abort(403)

    option_id = request.form.get("option_id", type=int)
    option = PollOption.query.filter_by(id=option_id, poll_id=poll.id).first()
    if option is None:
        return jsonify({"error": "invalid_option"}), 400

    existing_vote = PollVote.query.filter_by(poll_id=poll.id, user_id=current_user.id).first()
    if existing_vote is not None:
        existing_vote.option_id = option.id
    else:
        db.session.add(PollVote(poll_id=poll.id, option_id=option.id, user_id=current_user.id))
    db.session.commit()

    return jsonify(_serialize_poll(poll))


@bp_chat.route("/api/chat/<int:conversation_id>/history")
@login_required
def api_history(conversation_id: int):
    conversation = Conversation.query.get_or_404(conversation_id)
    if not chat_service.is_participant(conversation, current_user):
        abort(403)

    before_id = request.args.get("before", type=int)
    limit = min(request.args.get("limit", type=int, default=10), 50)
    if before_id is None:
        return jsonify([])

    messages = (
        ChatMessage.query.filter(
            ChatMessage.conversation_id == conversation_id, ChatMessage.id < before_id
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    messages.reverse()

    return jsonify([_serialize_message(m) for m in messages])


@bp_chat.route("/api/chat/<int:conversation_id>/messages")
@login_required
def api_messages(conversation_id: int):
    conversation = Conversation.query.get_or_404(conversation_id)
    if not chat_service.is_participant(conversation, current_user):
        abort(403)

    after_id = request.args.get("after", type=int, default=0)
    messages = ChatMessage.query.filter(
        ChatMessage.conversation_id == conversation_id, ChatMessage.id > after_id
    ).order_by(ChatMessage.created_at).all()

    if messages:
        chat_service.mark_read(conversation, current_user)

    return jsonify([_serialize_message(m) for m in messages])
