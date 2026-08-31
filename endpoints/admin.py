import os
from datetime import datetime
from functools import wraps

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload, selectinload

from library.extensions import db
from library.models.admin_action import AdminAction
from library.models.band import Band
from library.models.band_join_request import BandJoinRequest
from library.models.chat_message import ChatMessage
from library.models.conversation import Conversation
from library.models.conversation_participant import ConversationParticipant
from library.models.landmark import Landmark
from library.models.news_feed_event import NewsFeedEvent
from library.models.tag_point import TagPoint
from library.models.tag_report import TagReport
from library.models.user import User
from library.services.landmark_service import LandmarkService
from library.services.settings_service import DEFAULT_SETTINGS, SettingsService
from library.services.territory_engine import TerritoryEngine
from library.services.translator import t

bp_admin = Blueprint("admin", __name__, url_prefix="/admin")
landmark_service = LandmarkService()
settings_service = SettingsService()

MODEL_FILENAME = "tag_detector.onnx"

# Display order for the admin settings page - game-balance/anti-cheat values first, validation limits after.
SETTINGS_DISPLAY_ORDER = [
    "tag_radius_meters",
    "cluster_link_multiplier",
    "log_visit_max_distance_meters",
    "max_travel_speed_kmh",
    "teleport_distance_tolerance_meters",
    "local_leaderboard_radius_km",
    "overpass_timeout_seconds",
    "username_min_length",
    "username_max_length",
    "poll_min_options",
    "poll_max_options",
]


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@bp_admin.route("/")
@admin_required
def dashboard():
    return redirect(url_for("admin.queue"))


@bp_admin.route("/queue")
@admin_required
def queue():
    return render_template("admin/queue.html")


@bp_admin.route("/api/queue")
@admin_required
def queue_api():
    offset = request.args.get("offset", type=int, default=0)
    limit = min(request.args.get("limit", type=int, default=10), 50)
    reports = (
        TagReport.query.filter_by(resolved=False)
        .order_by(TagReport.created_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return jsonify(
        [
            {
                "report_id": report.id,
                "tag_point_id": report.tag_point.id,
                "band_name": report.tag_point.band.name,
                "reporter": report.reported_by.username,
                "reason": report.reason,
            }
            for report in reports
        ]
    )


@bp_admin.route("/reports/<int:report_id>/resolve", methods=["POST"])
@admin_required
def resolve_report(report_id: int):
    report = TagReport.query.get_or_404(report_id)
    action = request.form.get("action")

    if action == "remove_tag":
        affected_band = report.tag_point.band
        report.tag_point.status = "removed"
        report.tag_point.removed_reason = report.reason
        db.session.add(
            AdminAction(
                admin_id=current_user.id,
                action_type="remove_tag",
                target_description=f"TagPoint #{report.tag_point.id}",
                reason=report.reason,
            )
        )

    report.resolved = True
    report.resolved_at = datetime.utcnow()
    db.session.commit()

    if action == "remove_tag":
        TerritoryEngine.from_settings().recompute_all()
        landmark_service.refresh_for_band(affected_band)

    flash(t("flash.report_closed"), "success")
    return redirect(url_for("admin.queue"))


@bp_admin.route("/users")
@admin_required
def users():
    return render_template("admin/users.html")


@bp_admin.route("/api/users")
@admin_required
def users_api():
    offset = request.args.get("offset", type=int, default=0)
    limit = min(request.args.get("limit", type=int, default=10), 50)
    all_users = (
        User.query.options(joinedload(User.band))
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return jsonify(
        [
            {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "band_name": user.band.name if user.band else None,
                "registered_at": user.created_at.strftime("%Y.%m.%d"),
                "is_admin": user.is_admin,
                "is_banned": user.is_banned,
            }
            for user in all_users
        ]
    )


@bp_admin.route("/users/<int:user_id>/toggle-ban", methods=["POST"])
@admin_required
def toggle_ban(user_id: int):
    user = User.query.get_or_404(user_id)
    user.is_banned = not user.is_banned
    db.session.add(
        AdminAction(
            admin_id=current_user.id,
            action_type="ban" if user.is_banned else "unban",
            target_description=f"User #{user.id} ({user.username})",
        )
    )
    db.session.commit()
    flash(t("flash.user_status_updated"), "success")
    return redirect(url_for("admin.users"))


@bp_admin.route("/bands")
@admin_required
def bands():
    return render_template("admin/bands.html")


@bp_admin.route("/api/bands")
@admin_required
def bands_api():
    offset = request.args.get("offset", type=int, default=0)
    limit = min(request.args.get("limit", type=int, default=10), 50)
    all_bands = (
        Band.query.options(joinedload(Band.territory), selectinload(Band.members))
        .order_by(Band.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return jsonify(
        [
            {
                "band_id": band.id,
                "name": band.name,
                "leaders": ", ".join(m.username for m in band.members if m.band_role == "leader"),
                "member_count": len(band.members),
                "area_km2": round(band.territory.area_km2, 2) if band.territory else 0,
            }
            for band in all_bands
        ]
    )


@bp_admin.route("/bands/<int:band_id>/delete", methods=["POST"])
@admin_required
def delete_band(band_id: int):
    band = Band.query.get_or_404(band_id)

    for member in list(band.members):
        member.band_id = None
        member.band_role = None
        member.band_joined_at = None

    TagPoint.query.filter_by(band_id=band.id).delete()
    BandJoinRequest.query.filter_by(band_id=band.id).delete()
    Landmark.query.filter_by(band_id=band.id).delete()
    NewsFeedEvent.query.filter_by(band_id=band.id).delete()

    band_conversation = Conversation.query.filter_by(kind="band", band_id=band.id).first()
    if band_conversation is not None:
        ChatMessage.query.filter_by(conversation_id=band_conversation.id).delete()
        ConversationParticipant.query.filter_by(conversation_id=band_conversation.id).delete()
        db.session.delete(band_conversation)

    db.session.add(
        AdminAction(
            admin_id=current_user.id,
            action_type="delete_band",
            target_description=f"Band #{band.id} ({band.name})",
        )
    )
    db.session.delete(band)
    db.session.commit()

    TerritoryEngine.from_settings().recompute_all()
    flash(t("flash.band_deleted"), "success")
    return redirect(url_for("admin.bands"))


@bp_admin.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    if request.method == "POST":
        for key in DEFAULT_SETTINGS:
            raw_value = request.form.get(key)
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue
            settings_service.set(key, value)

        db.session.add(
            AdminAction(admin_id=current_user.id, action_type="update_settings", target_description="Site settings")
        )
        db.session.commit()
        flash(t("flash.settings_saved"), "success")
        return redirect(url_for("admin.settings"))

    current_values = settings_service.get_all()
    settings_list = [
        {
            "key": key,
            "value": current_values[key],
            "label": t(f"setting.{key}_label"),
            "description": t(f"setting.{key}_description"),
        }
        for key in SETTINGS_DISPLAY_ORDER
    ]
    return render_template("admin/settings.html", settings=settings_list)


@bp_admin.route("/model", methods=["GET", "POST"])
@admin_required
def model():
    models_root = current_app.config["MODELS_ROOT"]
    model_path = os.path.join(models_root, MODEL_FILENAME)

    if request.method == "POST":
        uploaded_file = request.files.get("model_file")
        if uploaded_file is None or uploaded_file.filename == "":
            flash(t("flash.model_upload_missing"), "error")
            return redirect(url_for("admin.model"))

        if not uploaded_file.filename.lower().endswith(".onnx"):
            flash(t("flash.model_upload_invalid_type"), "error")
            return redirect(url_for("admin.model"))

        os.makedirs(models_root, exist_ok=True)
        uploaded_file.save(model_path)

        db.session.add(
            AdminAction(
                admin_id=current_user.id, action_type="update_model", target_description="Tag detection model"
            )
        )
        db.session.commit()
        flash(t("flash.model_uploaded"), "success")
        return redirect(url_for("admin.model"))

    model_info = None
    if os.path.exists(model_path):
        file_stat = os.stat(model_path)
        model_info = {
            "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
            "modified_at": datetime.fromtimestamp(file_stat.st_mtime),
        }
    return render_template("admin/model.html", model_info=model_info)
