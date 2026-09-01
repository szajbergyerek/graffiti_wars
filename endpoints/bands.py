import re
from datetime import datetime

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

from library.extensions import db
from library.i18n.countries import COUNTRIES, COUNTRY_BY_CODE
from library.models.band import BAND_COLOR_PALETTE, JOIN_POLICIES, Band
from library.models.band_join_request import BandJoinRequest
from library.models.band_territory import BandTerritory
from library.models.conversation import Conversation
from library.models.conversation_participant import ConversationParticipant
from library.models.landmark import Landmark
from library.models.news_feed_event import NewsFeedEvent
from library.models.tag_point import TagPoint
from library.models.user import User
from library.services.chat_service import ChatService
from library.services.image_storage import ImageStorage
from library.services.leaderboard_service import LeaderboardService
from library.services.settings_service import SettingsService
from library.services.territory_engine import TerritoryEngine
from library.services.translator import t
from library.services.username_validator import UsernameValidator

HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")

bp_bands = Blueprint("bands", __name__, url_prefix="/bands")
chat_service = ChatService()
username_validator = UsernameValidator()
leaderboard_service = LeaderboardService()
settings_service = SettingsService()


def _query_bands(query_text, sort_key, scope, join_policy_filter, lat=None, lon=None):
    bands = Band.query.filter(Band.is_deleted.is_(False)).options(
        joinedload(Band.territory), selectinload(Band.members)
    )

    if query_text:
        bands = bands.filter(Band.name.ilike(f"%{query_text}%"))
    if join_policy_filter in JOIN_POLICIES:
        bands = bands.filter(Band.join_policy == join_policy_filter)

    bands = bands.all()

    if scope == "national":
        nationality_code = current_user.nationality_code if current_user.is_authenticated else None
        bands = [band for band in bands if nationality_code and band.nationality_code == nationality_code]
    elif scope == "local":
        if lat is not None and lon is not None:
            local_band_ids = {
                row.band.id
                for row in leaderboard_service.local_band_ranking(
                    lat, lon, radius_km=settings_service.get("local_leaderboard_radius_km")
                )
            }
            bands = [band for band in bands if band.id in local_band_ids]
        else:
            bands = []

    tag_counts = dict(
        db.session.query(TagPoint.band_id, func.count(TagPoint.id))
        .filter(TagPoint.status == "approved", TagPoint.band_id.isnot(None))
        .group_by(TagPoint.band_id)
        .all()
    )

    if sort_key == "area":
        bands.sort(key=lambda band: band.territory.area_km2 if band.territory else 0, reverse=True)
    elif sort_key == "members":
        bands.sort(key=lambda band: len(band.members), reverse=True)
    elif sort_key == "tags":
        bands.sort(key=lambda band: tag_counts.get(band.id, 0), reverse=True)
    else:
        bands.sort(key=lambda band: band.created_at, reverse=True)

    return bands, tag_counts


@bp_bands.route("/")
def list_bands():
    return render_template(
        "band_list.html",
        query_text=request.args.get("q", "").strip(),
        sort_key=request.args.get("sort", "newest"),
        scope=request.args.get("scope", "global"),
        join_policy_filter=request.args.get("join_policy", "all"),
    )


@bp_bands.route("/api/list")
def list_bands_api():
    bands, tag_counts = _query_bands(
        query_text=request.args.get("q", "").strip(),
        sort_key=request.args.get("sort", "newest"),
        scope=request.args.get("scope", "global"),
        join_policy_filter=request.args.get("join_policy", "all"),
        lat=request.args.get("lat", type=float),
        lon=request.args.get("lon", type=float),
    )

    offset = request.args.get("offset", type=int, default=0)
    limit = min(request.args.get("limit", type=int, default=10), 50)
    page = bands[offset : offset + limit]

    return jsonify(
        [
            {
                "band_id": band.id,
                "name": band.name,
                "color": band.color,
                "description": band.description,
                "member_count": len(band.members),
                "tag_count": tag_counts.get(band.id, 0),
                "area_km2": round(band.territory.area_km2, 2) if band.territory else 0,
                "join_policy": band.join_policy,
            }
            for band in page
        ]
    )


@bp_bands.route("/create", methods=["GET", "POST"])
@login_required
def create_band():
    if not current_user.is_civilian:
        flash(t("flash.must_leave_band_first"), "error")
        return redirect(url_for("bands.band_detail", band_id=current_user.band_id))

    if request.method == "POST":
        name = request.form["name"].strip()
        description = request.form.get("description", "").strip()
        join_policy = request.form.get("join_policy", "open")
        if join_policy not in JOIN_POLICIES:
            join_policy = "open"
        color = request.form.get("color", "")
        if not HEX_COLOR_PATTERN.match(color):
            color = Band.next_color(Band.query.count())
        nationality_code = request.form.get("nationality_code") or None
        if nationality_code and nationality_code not in COUNTRY_BY_CODE:
            nationality_code = None
        reference_image = request.files.get("reference_image")

        if not name or reference_image is None or reference_image.filename == "":
            flash(t("flash.band_missing_fields"), "error")
            return render_template("band_create.html", countries=COUNTRIES)

        if Band.query.filter_by(name=name).first():
            flash(t("flash.band_name_taken"), "error")
            return render_template("band_create.html", countries=COUNTRIES)

        storage = ImageStorage(current_app.config["IMAGES_ROOT"])
        try:
            image = storage.save(reference_image, "tags", uploaded_by_id=current_user.id)
        except ValueError:
            flash(t("flash.unsupported_image"), "error")
            return render_template("band_create.html", countries=COUNTRIES)

        band = Band(
            name=name,
            description=description,
            reference_image_id=image.id,
            color=color,
            nationality_code=nationality_code,
            join_policy=join_policy,
            founder_id=current_user.id,
        )
        db.session.add(band)
        db.session.flush()

        current_user.band_id = band.id
        current_user.band_role = "leader"
        current_user.band_joined_at = datetime.utcnow()

        chat_service.create_band_conversation(band)

        db.session.add(
            NewsFeedEvent(event_type="band_created", band_id=band.id, message=t("feed.band_created", band=band.name))
        )
        db.session.commit()

        flash(t("flash.band_created"), "success")
        return redirect(url_for("bands.band_detail", band_id=band.id))

    return render_template("band_create.html", countries=COUNTRIES)


@bp_bands.route("/<int:band_id>")
def band_detail(band_id: int):
    band = Band.query.get_or_404(band_id)
    if band.is_deleted:
        abort(404)
    member_count = User.query.filter_by(band_id=band.id).count()
    total_approved = TagPoint.query.filter_by(band_id=band.id, status="approved").count()
    territory = db.session.get(BandTerritory, band.id)

    is_leader = current_user.is_authenticated and current_user.band_id == band.id and current_user.band_role == "leader"
    own_pending_request = None
    pending_requests = []
    if current_user.is_authenticated:
        own_pending_request = BandJoinRequest.query.filter_by(
            band_id=band.id, user_id=current_user.id, status="pending"
        ).first()
    if is_leader:
        pending_requests = BandJoinRequest.query.filter_by(band_id=band.id, status="pending").all()

    landmark_count = Landmark.query.filter(
        Landmark.band_id == band.id, Landmark.name.isnot(None), Landmark.name != ""
    ).count()

    return render_template(
        "band_detail.html",
        band=band,
        member_count=member_count,
        total_approved=total_approved,
        territory=territory,
        is_leader=is_leader,
        own_pending_request=own_pending_request,
        pending_requests=pending_requests,
        landmark_count=landmark_count,
    )


@bp_bands.route("/<int:band_id>/api/members")
def band_members_api(band_id: int):
    Band.query.get_or_404(band_id)
    offset = request.args.get("offset", type=int, default=0)
    limit = min(request.args.get("limit", type=int, default=10), 50)
    is_leader = current_user.is_authenticated and current_user.band_id == band_id and current_user.band_role == "leader"

    members = (
        User.query.filter_by(band_id=band_id)
        .order_by(User.band_joined_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return jsonify(
        [
            {
                "user_id": member.id,
                "username": member.username,
                "joined_at": member.band_joined_at.strftime("%Y.%m.%d") if member.band_joined_at else None,
                "verified_count": TagPoint.query.filter_by(
                    band_id=band_id, submitted_by_id=member.id, status="approved"
                ).count(),
                "role": member.band_role,
                "can_kick": is_leader and member.id != current_user.id,
            }
            for member in members
        ]
    )


@bp_bands.route("/<int:band_id>/api/landmarks")
def band_landmarks_api(band_id: int):
    Band.query.get_or_404(band_id)
    offset = request.args.get("offset", type=int, default=0)
    limit = min(request.args.get("limit", type=int, default=10), 50)

    landmarks = (
        Landmark.query.filter(
            Landmark.band_id == band_id, Landmark.name.isnot(None), Landmark.name != ""
        )
        .order_by(Landmark.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return jsonify(
        [
            {
                "name": landmark.name,
                "subtype": landmark.subtype,
                "category": landmark.category,
                "lat": landmark.lat,
                "lon": landmark.lon,
            }
            for landmark in landmarks
        ]
    )


@bp_bands.route("/<int:band_id>/join", methods=["POST"])
@login_required
def join_band(band_id: int):
    band = Band.query.get_or_404(band_id)
    if band.is_deleted:
        abort(404)
    if not current_user.is_civilian:
        flash(t("flash.already_member"), "error")
        return redirect(url_for("bands.band_detail", band_id=band_id))
    if band.join_policy != "open":
        flash(t("flash.band_closed"), "error")
        return redirect(url_for("bands.band_detail", band_id=band_id))

    _add_member(band, current_user)
    db.session.commit()

    flash(t("flash.joined_band", band=band.name), "success")
    return redirect(url_for("bands.band_detail", band_id=band_id))


@bp_bands.route("/<int:band_id>/request-join", methods=["POST"])
@login_required
def request_join(band_id: int):
    band = Band.query.get_or_404(band_id)
    if band.is_deleted:
        abort(404)
    if not current_user.is_civilian:
        flash(t("flash.already_member"), "error")
        return redirect(url_for("bands.band_detail", band_id=band_id))
    if band.join_policy != "request":
        abort(400)

    existing = BandJoinRequest.query.filter_by(band_id=band.id, user_id=current_user.id, status="pending").first()
    if existing is not None:
        flash(t("flash.join_request_already_sent"), "error")
        return redirect(url_for("bands.band_detail", band_id=band_id))

    db.session.add(BandJoinRequest(band_id=band.id, user_id=current_user.id))
    db.session.commit()

    flash(t("flash.join_request_sent"), "success")
    return redirect(url_for("bands.band_detail", band_id=band_id))


@bp_bands.route("/requests/<int:request_id>/approve", methods=["POST"])
@login_required
def approve_join_request(request_id: int):
    join_request = BandJoinRequest.query.get_or_404(request_id)
    band = join_request.band
    if current_user.id != band.founder_id and current_user.band_role != "leader":
        abort(403)
    if current_user.band_id != band.id:
        abort(403)

    if join_request.status == "pending" and join_request.user.is_civilian:
        _add_member(band, join_request.user)
    join_request.status = "approved"
    db.session.commit()

    flash(t("flash.join_request_approved"), "success")
    return redirect(url_for("bands.band_detail", band_id=band.id))


@bp_bands.route("/requests/<int:request_id>/reject", methods=["POST"])
@login_required
def reject_join_request(request_id: int):
    join_request = BandJoinRequest.query.get_or_404(request_id)
    band = join_request.band
    if current_user.id != band.founder_id and current_user.band_role != "leader":
        abort(403)
    if current_user.band_id != band.id:
        abort(403)

    join_request.status = "rejected"
    db.session.commit()

    flash(t("flash.join_request_rejected"), "success")
    return redirect(url_for("bands.band_detail", band_id=band.id))


@bp_bands.route("/<int:band_id>/add-member", methods=["POST"])
@login_required
def add_member(band_id: int):
    band = Band.query.get_or_404(band_id)
    if current_user.band_id != band.id or current_user.band_role != "leader":
        abort(403)

    username = username_validator.normalize(request.form.get("username", ""))
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(t("flash.user_not_found"), "error")
        return redirect(url_for("bands.band_detail", band_id=band_id))
    if not user.is_civilian:
        flash(t("flash.user_not_civilian"), "error")
        return redirect(url_for("bands.band_detail", band_id=band_id))

    _add_member(band, user)
    db.session.commit()

    flash(t("flash.member_added", username=user.username), "success")
    return redirect(url_for("bands.band_detail", band_id=band_id))


def _add_member(band: Band, user: User) -> None:
    user.band_id = band.id
    user.band_role = "member"
    user.band_joined_at = datetime.utcnow()
    chat_service.add_band_member(band, user)
    db.session.add(
        NewsFeedEvent(
            event_type="member_joined",
            band_id=band.id,
            message=t("feed.member_joined", username=user.username, band=band.name),
        )
    )


def _require_leader(band: Band) -> None:
    if current_user.band_id != band.id or current_user.band_role != "leader":
        abort(403)


def _delete_band(band: Band) -> None:
    """
    Disband a band without erasing anything - every deletion in this app is
    logical only. The band, its tags, its chat history and everything else
    tied to it stays in the database (and any files stay on disk) for later
    use; this just hides all of it from the game and marks the band's own
    tags as removed so they drop off the map/territory like any other
    removed tag. Pending join requests are the one exception - they're
    disposable, not content, so those are actually deleted.
    """
    for member in list(band.members):
        member.band_id = None
        member.band_role = None
        member.band_joined_at = None

    TagPoint.query.filter_by(band_id=band.id, status="approved").update(
        {"status": "removed", "removed_reason": "Band disbanded"}
    )
    BandJoinRequest.query.filter_by(band_id=band.id, status="pending").delete()

    band_conversation = Conversation.query.filter_by(kind="band", band_id=band.id).first()
    if band_conversation is not None:
        # Only the "who currently sees this conversation" membership is
        # cleared - the conversation and every message in it stay intact.
        ConversationParticipant.query.filter_by(conversation_id=band_conversation.id).delete()

    band.is_deleted = True
    band.deleted_at = datetime.utcnow()


def _delete_band_if_empty(band: Band) -> bool:
    """Disband a band that no longer has any members. Returns True if it was disbanded."""
    if User.query.filter_by(band_id=band.id).count() > 0:
        return False
    _delete_band(band)
    return True


@bp_bands.route("/<int:band_id>/disband", methods=["POST"])
@login_required
def disband_band(band_id: int):
    band = Band.query.get_or_404(band_id)
    _require_leader(band)

    band_name = band.name
    _delete_band(band)
    db.session.commit()

    TerritoryEngine.from_settings().recompute_all()
    flash(t("flash.band_disbanded", band=band_name), "success")
    return redirect(url_for("index.index"))


@bp_bands.route("/<int:band_id>/settings", methods=["GET", "POST"])
@login_required
def band_settings(band_id: int):
    band = Band.query.get_or_404(band_id)
    _require_leader(band)

    if request.method == "POST":
        description = request.form.get("description", "").strip()
        join_policy = request.form.get("join_policy", band.join_policy)
        if join_policy not in JOIN_POLICIES:
            join_policy = band.join_policy
        nationality_code = request.form.get("nationality_code") or None
        if nationality_code and nationality_code not in COUNTRY_BY_CODE:
            nationality_code = None
        color = request.form.get("color", "")
        if not HEX_COLOR_PATTERN.match(color):
            color = band.color

        storage = ImageStorage(current_app.config["IMAGES_ROOT"])

        reference_image = request.files.get("reference_image")
        if reference_image and reference_image.filename:
            try:
                image = storage.save(reference_image, "tags", uploaded_by_id=current_user.id)
            except ValueError:
                flash(t("flash.unsupported_image"), "error")
                return render_template("band_settings.html", band=band, countries=COUNTRIES)
            band.reference_image_id = image.id

        banner_image = request.files.get("banner")
        if banner_image and banner_image.filename:
            try:
                image = storage.save(banner_image, "tags", uploaded_by_id=current_user.id)
            except ValueError:
                flash(t("flash.unsupported_image"), "error")
                return render_template("band_settings.html", band=band, countries=COUNTRIES)
            band.banner_image_id = image.id

        band.description = description
        band.join_policy = join_policy
        band.nationality_code = nationality_code
        band.color = color
        db.session.commit()

        flash(t("flash.band_settings_updated"), "success")
        return redirect(url_for("bands.band_detail", band_id=band.id))

    return render_template("band_settings.html", band=band, countries=COUNTRIES)


@bp_bands.route("/<int:band_id>/members/<int:user_id>/kick", methods=["POST"])
@login_required
def kick_member(band_id: int, user_id: int):
    band = Band.query.get_or_404(band_id)
    _require_leader(band)

    if user_id == current_user.id:
        flash(t("flash.cannot_kick_self"), "error")
        return redirect(url_for("bands.band_detail", band_id=band_id))

    member = User.query.get_or_404(user_id)
    if member.band_id != band.id:
        abort(404)

    chat_service.remove_band_member(band, member)
    member.band_id = None
    member.band_role = None
    member.band_joined_at = None
    db.session.flush()

    band_deleted = _delete_band_if_empty(band)
    db.session.commit()
    if band_deleted:
        TerritoryEngine.from_settings().recompute_all()

    flash(t("flash.member_kicked", username=member.username), "success")
    if band_deleted:
        return redirect(url_for("index.index"))
    return redirect(url_for("bands.band_detail", band_id=band_id))


@bp_bands.route("/leave", methods=["POST"])
@login_required
def leave_band():
    if current_user.is_civilian:
        abort(400)

    band = current_user.band
    chat_service.remove_band_member(band, current_user)

    current_user.band_id = None
    current_user.band_role = None
    current_user.band_joined_at = None
    db.session.flush()

    band_deleted = _delete_band_if_empty(band)
    db.session.commit()
    if band_deleted:
        TerritoryEngine.from_settings().recompute_all()

    flash(t("flash.left_band"), "success")
    return redirect(url_for("index.index"))
