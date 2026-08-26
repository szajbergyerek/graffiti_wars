from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from library.models.chat_message import ChatMessage
from library.models.conversation import Conversation
from library.models.conversation_participant import ConversationParticipant
from library.models.user import User
from library.services.chat_service import ChatService
from library.services.translator import t

bp_chat = Blueprint("chat", __name__)
chat_service = ChatService()


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


@bp_chat.route("/chat")
@login_required
def inbox():
    conversation_ids = [
        p.conversation_id
        for p in ConversationParticipant.query.filter_by(user_id=current_user.id).all()
    ]
    conversations = Conversation.query.filter(Conversation.id.in_(conversation_ids)).all()
    items = [_conversation_display(c) for c in conversations]
    items.sort(key=lambda item: item["last_message"].created_at if item["last_message"] else item["conversation"].created_at, reverse=True)
    return render_template("chat_inbox.html", items=items)


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
    return render_template(
        "chat_conversation.html",
        conversation=conversation,
        title=display["title"],
        messages=conversation.messages,
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

    return jsonify(
        [
            {
                "id": m.id,
                "sender": m.sender.username,
                "sender_avatar": m.sender.display_avatar_url,
                "body": m.body,
                "is_own": m.sender_id == current_user.id,
                "created_at": m.created_at.strftime("%Y.%m.%d %H:%M"),
            }
            for m in messages
        ]
    )
