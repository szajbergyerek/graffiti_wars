import logging
import os
from datetime import datetime

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from library.extensions import db
from library.models.chat_message import ChatMessage
from library.models.conversation import Conversation
from library.models.image import Image
from library.models.news_feed_event import NewsFeedEvent
from library.models.tag_comment import TagComment
from library.models.tag_point import TagPoint
from library.models.tag_report import TagReport
from library.models.tag_visit import TagVisit
from library.services.exif_extractor import ExifExtractor
from library.services.image_storage import ImageStorage
from library.services.landmark_service import LandmarkService
from library.services.territory_engine import TerritoryEngine
from library.services.translator import t

bp_tags = Blueprint("tags", __name__)
landmark_service = LandmarkService()

MAX_PHOTO_AGE_SECONDS = 60

logger = logging.getLogger("tag_submission")


@bp_tags.route("/map")
def map_view():
    map_center = None
    if current_user.is_authenticated and not current_user.is_civilian:
        own_points = TagPoint.query.filter_by(band_id=current_user.band_id, status="approved").all()
        if own_points:
            map_center = [
                sum(p.lat for p in own_points) / len(own_points),
                sum(p.lon for p in own_points) / len(own_points),
            ]

    return render_template("map.html", map_center=map_center)


def _get_own_pending_image(image_id: int) -> Image:
    image = Image.query.get_or_404(image_id)
    if image.uploaded_by_id != current_user.id:
        raise PermissionError
    if TagPoint.query.filter_by(photo_image_id=image.id).first() is not None:
        raise ValueError("This image was already used for a tag submission.")
    return image


@bp_tags.route("/tags/submit", methods=["GET", "POST"])
@login_required
def submit_tag():
    if current_user.is_civilian:
        flash(t("flash.members_only"), "error")
        return redirect(url_for("bands.list_bands"))

    if request.method == "POST":
        photo = request.files.get("photo")
        client_now_raw = request.form.get("client_now")
        description = request.form.get("description", "").strip()[:500]

        if photo is None or photo.filename == "" or not client_now_raw:
            flash(t("flash.tag_missing_fields"), "error")
            return render_template("tag_submit_upload.html")

        try:
            client_now = datetime.fromisoformat(client_now_raw)
        except ValueError:
            client_now = datetime.utcnow()

        images_root = current_app.config["IMAGES_ROOT"]
        storage = ImageStorage(images_root)
        try:
            image = storage.save(photo, "tags", uploaded_by_id=current_user.id, subfolder=str(current_user.band_id))
        except ValueError:
            flash(t("flash.unsupported_image"), "error")
            return render_template("tag_submit_upload.html")

        metadata = ExifExtractor().extract(os.path.join(images_root, image.relative_path))
        logger.info(
            "Tag photo uploaded by %s: image_id=%s client_now=%s metadata=%s",
            current_user.username, image.id, client_now, metadata,
        )

        date_taken = metadata["date_taken"]
        if date_taken is None:
            flash(t("flash.photo_no_capture_time"), "error")
            return render_template("tag_submit_upload.html")

        age_seconds = abs((client_now - date_taken).total_seconds())
        if age_seconds > MAX_PHOTO_AGE_SECONDS:
            flash(t("flash.photo_too_old"), "error")
            return render_template("tag_submit_upload.html")

        db.session.commit()

        if metadata["gps_lat"] is not None and metadata["gps_lon"] is not None:
            return redirect(
                url_for(
                    "tags.processing",
                    image_id=image.id,
                    lat=metadata["gps_lat"],
                    lon=metadata["gps_lon"],
                    description=description,
                )
            )

        return redirect(url_for("tags.locate", image_id=image.id, description=description))

    return render_template("tag_submit_upload.html")


@bp_tags.route("/tags/submit/locate")
@login_required
def locate():
    image_id = request.args.get("image_id", type=int)
    description = request.args.get("description", "")
    try:
        _get_own_pending_image(image_id)
    except (PermissionError, ValueError):
        return redirect(url_for("tags.submit_tag"))

    return render_template("tag_submit_locate.html", image_id=image_id, description=description)


@bp_tags.route("/tags/submit/cancel", methods=["POST"])
@login_required
def cancel_submission():
    image_id = request.form.get("image_id", type=int)
    image = Image.query.filter_by(id=image_id, uploaded_by_id=current_user.id).first()
    if image is not None and TagPoint.query.filter_by(photo_image_id=image.id).first() is None:
        db.session.delete(image)
        db.session.commit()

    flash(t("flash.submission_cancelled"), "success")
    return redirect(url_for("tags.map_view"))


@bp_tags.route("/tags/submit/processing")
@login_required
def processing():
    image_id = request.args.get("image_id", type=int)
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    description = request.args.get("description", "")
    try:
        _get_own_pending_image(image_id)
    except (PermissionError, ValueError):
        return redirect(url_for("tags.submit_tag"))
    if lat is None or lon is None:
        return redirect(url_for("tags.submit_tag"))

    return render_template(
        "tag_submit_processing.html", image_id=image_id, lat=lat, lon=lon, description=description
    )


@bp_tags.route("/tags/submit/finalize", methods=["POST"])
@login_required
def finalize():
    image_id = request.form.get("image_id", type=int)
    lat = request.form.get("lat", type=float)
    lon = request.form.get("lon", type=float)
    description = request.form.get("description", "").strip()[:500]

    try:
        image = _get_own_pending_image(image_id)
    except PermissionError:
        return jsonify({"error": "forbidden"}), 403
    except ValueError:
        return jsonify({"error": "already_used"}), 400

    if lat is None or lon is None:
        return jsonify({"error": "missing_location"}), 400

    # The real AI verification model isn't ready yet - every submission is approved for now.
    tag_point = TagPoint(
        band_id=current_user.band_id,
        submitted_by_id=current_user.id,
        photo_image_id=image.id,
        lat=lat,
        lon=lon,
        status="approved",
        description=description or None,
        ai_confidence=None,
    )
    db.session.add(tag_point)
    db.session.commit()

    TerritoryEngine(radius_meters=current_app.config["TAG_RADIUS_METERS"]).recompute_all()
    landmark_service.refresh_for_band(current_user.band)
    db.session.add(
        NewsFeedEvent(
            event_type="tag_approved",
            band_id=current_user.band_id,
            message=t("feed.tag_approved", band=current_user.band.name, username=current_user.username),
        )
    )

    band_conversation = Conversation.query.filter_by(kind="band", band_id=current_user.band_id).first()
    if band_conversation is not None:
        captured_new_ground = (tag_point.area_added_km2 or 0.0) > 0
        system_text = t(
            "chat.system_tag_captured" if captured_new_ground else "chat.system_tag_reinforced",
            username=current_user.username,
        )
        db.session.add(
            ChatMessage(
                conversation_id=band_conversation.id,
                sender_id=current_user.id,
                body=system_text,
                message_type="tag_added",
                tag_point_id=tag_point.id,
            )
        )

    db.session.commit()

    return jsonify({"redirect_url": url_for("tags.map_view")})


@bp_tags.route("/tags/<int:tag_id>")
def tag_detail(tag_id: int):
    tag_point = TagPoint.query.options(
        joinedload(TagPoint.submitted_by), joinedload(TagPoint.band), joinedload(TagPoint.photo_image)
    ).get_or_404(tag_id)
    area_added_km2 = tag_point.area_added_km2 or 0.0
    return render_template(
        "tag_detail.html",
        tag_point=tag_point,
        area_added_km2=area_added_km2,
    )


@bp_tags.route("/api/tags/<int:tag_id>/comments")
def list_comments(tag_id: int):
    offset = request.args.get("offset", type=int, default=0)
    limit = min(request.args.get("limit", type=int, default=10), 50)
    comments = (
        TagComment.query.filter_by(tag_point_id=tag_id)
        .options(joinedload(TagComment.user))
        .order_by(TagComment.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return jsonify(
        [
            {
                "id": c.id,
                "username": c.user.username,
                "avatar_url": c.user.display_avatar_url,
                "body": c.body,
                "created_at": c.created_at.strftime("%Y.%m.%d %H:%M"),
            }
            for c in comments
        ]
    )


@bp_tags.route("/tags/<int:tag_id>/comments", methods=["POST"])
@login_required
def post_comment(tag_id: int):
    TagPoint.query.get_or_404(tag_id)
    body = request.form.get("body", "").strip()[:1000]
    if not body:
        return jsonify({"error": "empty_body"}), 400

    comment = TagComment(tag_point_id=tag_id, user_id=current_user.id, body=body)
    db.session.add(comment)
    db.session.commit()

    return jsonify(
        {
            "id": comment.id,
            "username": current_user.username,
            "avatar_url": current_user.display_avatar_url,
            "body": comment.body,
            "created_at": comment.created_at.strftime("%Y.%m.%d %H:%M"),
        }
    )


@bp_tags.route("/tags/<int:tag_id>/report", methods=["POST"])
@login_required
def report_tag(tag_id: int):
    tag_point = TagPoint.query.get_or_404(tag_id)
    reason = request.form.get("reason", "").strip()

    db.session.add(TagReport(tag_point_id=tag_point.id, reported_by_id=current_user.id, reason=reason))
    db.session.commit()

    flash(t("flash.report_thanks"), "success")
    return redirect(url_for("tags.map_view"))


@bp_tags.route("/tags/<int:tag_id>/log", methods=["GET", "POST"])
@login_required
def log_visit(tag_id: int):
    tag_point = TagPoint.query.options(joinedload(TagPoint.band), joinedload(TagPoint.photo_image)).get_or_404(
        tag_id
    )

    if request.method == "POST":
        photo = request.files.get("photo")
        if photo is None or photo.filename == "":
            flash(t("flash.tag_missing_fields"), "error")
            return render_template("tag_log_upload.html", tag_point=tag_point)

        storage = ImageStorage(current_app.config["IMAGES_ROOT"])
        try:
            image = storage.save(photo, "tag_visits", uploaded_by_id=current_user.id)
        except ValueError:
            flash(t("flash.unsupported_image"), "error")
            return render_template("tag_log_upload.html", tag_point=tag_point)

        # Real photo/location matching against the tag isn't ready yet - every log is accepted for now.
        db.session.add(TagVisit(tag_point_id=tag_point.id, visitor_id=current_user.id, photo_image_id=image.id))
        db.session.commit()

        flash(t("flash.tag_logged"), "success")
        return redirect(url_for("tags.tag_detail", tag_id=tag_point.id))

    return render_template("tag_log_upload.html", tag_point=tag_point)


@bp_tags.route("/tags/search", methods=["GET", "POST"])
@login_required
def search_tag():
    if request.method == "POST":
        photo = request.files.get("photo")
        if photo is None or photo.filename == "":
            flash(t("flash.tag_missing_fields"), "error")
            return render_template("tag_search_upload.html")

        storage = ImageStorage(current_app.config["IMAGES_ROOT"])
        try:
            storage.save(photo, "tag_searches", uploaded_by_id=current_user.id)
        except ValueError:
            flash(t("flash.unsupported_image"), "error")
            return render_template("tag_search_upload.html")

        # The actual band-matching search isn't implemented yet - just accept the photo for now.
        flash(t("flash.tag_search_coming_soon"), "success")
        return redirect(url_for("tags.map_view"))

    return render_template("tag_search_upload.html")
