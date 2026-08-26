from datetime import datetime
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from library.extensions import db
from library.models.admin_action import AdminAction
from library.models.band import Band
from library.models.band_join_request import BandJoinRequest
from library.models.chat_message import ChatMessage
from library.models.conversation import Conversation
from library.models.conversation_participant import ConversationParticipant
from library.models.landmark import Landmark
from library.models.tag_point import TagPoint
from library.models.tag_report import TagReport
from library.models.user import User
from library.services.landmark_service import LandmarkService
from library.services.territory_engine import TerritoryEngine
from library.services.translator import t

bp_admin = Blueprint("admin", __name__, url_prefix="/admin")
landmark_service = LandmarkService()


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
    open_reports = TagReport.query.filter_by(resolved=False).order_by(TagReport.created_at.asc()).all()
    return render_template("admin/queue.html", open_reports=open_reports)


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
        TerritoryEngine().recompute_all()
        landmark_service.refresh_for_band(affected_band)

    flash(t("flash.report_closed"), "success")
    return redirect(url_for("admin.queue"))


@bp_admin.route("/users")
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)


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
    all_bands = Band.query.order_by(Band.created_at.desc()).all()
    return render_template("admin/bands.html", bands=all_bands)


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

    TerritoryEngine().recompute_all()
    flash(t("flash.band_deleted"), "success")
    return redirect(url_for("admin.bands"))
