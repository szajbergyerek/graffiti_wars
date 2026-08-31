import logging
import math
import threading
from datetime import datetime, timedelta

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from library.extensions import db
from library.models.band import Band
from library.models.chat_message import ChatMessage
from library.models.conversation import Conversation
from library.models.image import Image
from library.models.news_feed_event import NewsFeedEvent
from library.models.tag_comment import TagComment
from library.models.tag_point import TagPoint
from library.models.tag_report import TagReport
from library.models.tag_visit import TagVisit
from library.services.image_storage import ImageStorage
from library.services.landmark_service import LandmarkService
from library.services.settings_service import SettingsService
from library.services.territory_engine import TerritoryEngine
from library.services.translator import t

bp_tags = Blueprint("tags", __name__)
landmark_service = LandmarkService()
settings_service = SettingsService()

logger = logging.getLogger("tag_submission")

# Earth's radius is a physical constant, not an admin-editable setting.
EARTH_RADIUS_METERS = 6_371_000.0


def _distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Compute the great-circle distance between two lat/lon points.

    param lat1: Latitude of the first point, in degrees.
    param lon1: Longitude of the first point, in degrees.
    param lat2: Latitude of the second point, in degrees.
    param lon2: Longitude of the second point, in degrees.

    :return: The distance between the two points, in meters.
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_METERS * math.asin(math.sqrt(a))


def _is_valid_coordinate(lat: float, lon: float) -> bool:
    """
    Check that a lat/lon pair is within the physically valid range.

    param lat: Latitude in degrees.
    param lon: Longitude in degrees.

    :return: True if -90 <= lat <= 90 and -180 <= lon <= 180.
    """
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def _is_teleport(user, lat: float, lon: float, now: datetime) -> bool:
    """
    Flag a new location as implausible given the user's last accepted location.

    Compares the implied travel speed between the user's last known
    tag-submission/log location and this new one - if it's faster than any
    realistic mode of transport could cover, the new location is almost
    certainly spoofed (or the previous one was). A small distance tolerance
    absorbs ordinary GPS jitter between two near-simultaneous actions.

    param user: The current user, whose `last_location_lat/lon/at` fields hold their last accepted location.
    param lat: Latitude of the new location, in degrees.
    param lon: Longitude of the new location, in degrees.
    param now: The current timestamp, used to compute elapsed time since the last accepted location.

    :return: True if the implied travel speed is implausibly high.
    """
    if user.last_location_at is None or user.last_location_lat is None or user.last_location_lon is None:
        return False

    distance_m = _distance_meters(lat, lon, user.last_location_lat, user.last_location_lon)
    if distance_m <= settings_service.get("teleport_distance_tolerance_meters"):
        return False

    elapsed_seconds = max((now - user.last_location_at).total_seconds(), 1.0)
    implied_speed_kmh = (distance_m / 1000) / (elapsed_seconds / 3600)
    return implied_speed_kmh > settings_service.get("max_travel_speed_kmh")


def _exceeds_rate_limit(model, user_field, user_id: int, count_key: str, window_key: str) -> bool:
    """
    Check whether a user has already hit an admin-configured rate limit for
    some action, counting existing rows of the given model within a rolling
    time window.

    param model: The SQLAlchemy model to count rows of (e.g. TagPoint, TagVisit, TagComment).
    param user_field: The model's column that references the acting user (e.g. TagPoint.submitted_by_id).
    param user_id: The current user's id.
    param count_key: The SettingsService key for the max allowed count.
    param window_key: The SettingsService key for the time window, in minutes.

    :return: True if the user has already reached or exceeded the limit within the window.
    """
    since = datetime.utcnow() - timedelta(minutes=settings_service.get(window_key))
    recent_count = model.query.filter(user_field == user_id, model.created_at >= since).count()
    return recent_count >= settings_service.get(count_key)


def _has_recent_nearby_tag(user_id: int, lat: float, lon: float) -> bool:
    """
    Check whether the user already placed a (non-removed) tag close to this
    location within the admin-configured cooldown window - stops one person
    from farming territory by repeatedly re-tagging the same spot.

    param user_id: The submitting user's id.
    param lat: Latitude of the new tag, in degrees.
    param lon: Longitude of the new tag, in degrees.

    :return: True if a nearby recent tag from the same user exists.
    """
    since = datetime.utcnow() - timedelta(minutes=settings_service.get("duplicate_tag_window_minutes"))
    radius_m = settings_service.get("duplicate_tag_radius_meters")
    recent_points = TagPoint.query.filter(
        TagPoint.submitted_by_id == user_id,
        TagPoint.created_at >= since,
        TagPoint.status != "removed",
    ).all()
    return any(_distance_meters(lat, lon, point.lat, point.lon) <= radius_m for point in recent_points)


def _remember_location(user, lat: float, lon: float, now: datetime) -> None:
    """
    Record the user's latest accepted location, for future teleport checks.

    param user: The current user.
    param lat: Latitude of the accepted location, in degrees.
    param lon: Longitude of the accepted location, in degrees.
    param now: The timestamp of this location.

    :return: None.
    """
    user.last_location_lat = lat
    user.last_location_lon = lon
    user.last_location_at = now


def _refresh_landmarks_async(app, band_id: int) -> None:
    """
    Re-fetch a band's OpenStreetMap landmarks in a background thread.

    The public Overpass API can take up to its own 25s timeout to respond (or
    longer to fail), which is far too slow to hold up the tag-submission
    response for - this runs it off the request thread instead.

    param app: The real Flask app object (not the `current_app` proxy, which
        isn't valid outside a request context) needed to open a fresh app context.
    param band_id: The id of the band whose landmarks should be refreshed.

    :return: None.
    """
    with app.app_context():
        band = db.session.get(Band, band_id)
        if band is not None:
            landmark_service.refresh_for_band(band)


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
        lat = request.form.get("lat", type=float)
        lon = request.form.get("lon", type=float)

        if (
            photo is None or photo.filename == "" or not client_now_raw
            or lat is None or lon is None or not _is_valid_coordinate(lat, lon)
        ):
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

        # The photo comes from an in-page live camera capture and lat/lon from
        # the browser's Geolocation API, both captured right after the shutter
        # tap (see tag_submit_upload.html) - no EXIF/file-picker metadata is
        # involved and the location isn't user-editable.
        logger.info(
            "Tag photo uploaded by %s: image_id=%s client_now=%s lat=%s lon=%s",
            current_user.username, image.id, client_now, lat, lon,
        )

        db.session.commit()

        return redirect(url_for("tags.processing", image_id=image.id, lat=lat, lon=lon))

    return render_template("tag_submit_upload.html")


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
    if lat is None or lon is None or not _is_valid_coordinate(lat, lon):
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

    if lat is None or lon is None or not _is_valid_coordinate(lat, lon):
        return jsonify({"error": "missing_location"}), 400

    if _exceeds_rate_limit(
        TagPoint, TagPoint.submitted_by_id, current_user.id, "tag_submit_rate_limit_count", "tag_submit_rate_limit_window_minutes"
    ):
        flash(t("flash.rate_limited"), "error")
        return jsonify({"redirect_url": url_for("tags.map_view")})

    if _has_recent_nearby_tag(current_user.id, lat, lon):
        flash(t("flash.duplicate_tag_nearby"), "error")
        return jsonify({"redirect_url": url_for("tags.map_view")})

    now = datetime.utcnow()
    db.session.refresh(current_user._get_current_object(), with_for_update=True)
    if _is_teleport(current_user, lat, lon, now):
        flash(t("flash.teleport_detected"), "error")
        return jsonify({"redirect_url": url_for("tags.map_view")})

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
    _remember_location(current_user, lat, lon, now)
    db.session.commit()

    TerritoryEngine.from_settings().recompute_all()
    threading.Thread(
        target=_refresh_landmarks_async,
        args=(current_app._get_current_object(), current_user.band_id),
        daemon=True,
    ).start()
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

    return jsonify({"redirect_url": url_for("tags.tag_detail", tag_id=tag_point.id)})


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


@bp_tags.route("/tags/<int:tag_id>/description", methods=["POST"])
@login_required
def update_description(tag_id: int):
    tag_point = TagPoint.query.get_or_404(tag_id)
    if tag_point.submitted_by_id != current_user.id:
        abort(403)

    tag_point.description = request.form.get("description", "").strip()[:500] or None
    db.session.commit()

    return redirect(url_for("tags.tag_detail", tag_id=tag_id))


@bp_tags.route("/tags/<int:tag_id>/delete", methods=["POST"])
@login_required
def delete_tag(tag_id: int):
    tag_point = TagPoint.query.get_or_404(tag_id)
    if tag_point.submitted_by_id != current_user.id:
        abort(403)

    affected_band = tag_point.band
    tag_point.status = "removed"
    tag_point.removed_reason = "Deleted by submitter"
    db.session.commit()

    TerritoryEngine.from_settings().recompute_all()
    landmark_service.refresh_for_band(affected_band)

    flash(t("flash.tag_deleted"), "success")
    return redirect(url_for("tags.map_view"))


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

    if _exceeds_rate_limit(
        TagComment, TagComment.user_id, current_user.id, "tag_comment_rate_limit_count", "tag_comment_rate_limit_window_minutes"
    ):
        return jsonify({"error": "rate_limited"}), 429

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
    if tag_point.submitted_by_id == current_user.id:
        abort(403)

    reason = request.form.get("reason", "").strip()[:255]

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
    if tag_point.submitted_by_id == current_user.id:
        flash(t("flash.cannot_visit_own_tag"), "error")
        return redirect(url_for("tags.tag_detail", tag_id=tag_id))

    if request.method == "POST":
        photo = request.files.get("photo")
        lat = request.form.get("lat", type=float)
        lon = request.form.get("lon", type=float)

        if photo is None or photo.filename == "" or lat is None or lon is None or not _is_valid_coordinate(lat, lon):
            flash(t("flash.tag_missing_fields"), "error")
            return render_template(
                "tag_log_upload.html", tag_point=tag_point, max_distance_meters=settings_service.get("log_visit_max_distance_meters")
            )

        # The location comes from the browser's Geolocation API, captured right
        # before the camera opened (see tag_log_upload.html) - re-checked here
        # server-side too, since the client-side gate can be bypassed.
        if _distance_meters(lat, lon, tag_point.lat, tag_point.lon) > settings_service.get(
            "log_visit_max_distance_meters"
        ):
            flash(t("tag.log_too_far"), "error")
            return render_template(
                "tag_log_upload.html", tag_point=tag_point, max_distance_meters=settings_service.get("log_visit_max_distance_meters")
            )

        if _exceeds_rate_limit(
            TagVisit, TagVisit.visitor_id, current_user.id, "tag_visit_rate_limit_count", "tag_visit_rate_limit_window_minutes"
        ):
            flash(t("flash.rate_limited"), "error")
            return render_template(
                "tag_log_upload.html", tag_point=tag_point, max_distance_meters=settings_service.get("log_visit_max_distance_meters")
            )

        now = datetime.utcnow()
        db.session.refresh(current_user._get_current_object(), with_for_update=True)
        if _is_teleport(current_user, lat, lon, now):
            flash(t("flash.teleport_detected"), "error")
            return render_template(
                "tag_log_upload.html", tag_point=tag_point, max_distance_meters=settings_service.get("log_visit_max_distance_meters")
            )

        storage = ImageStorage(current_app.config["IMAGES_ROOT"])
        try:
            image = storage.save(photo, "tag_visits", uploaded_by_id=current_user.id)
        except ValueError:
            flash(t("flash.unsupported_image"), "error")
            return render_template(
                "tag_log_upload.html", tag_point=tag_point, max_distance_meters=settings_service.get("log_visit_max_distance_meters")
            )

        # Real photo matching against the tag isn't ready yet - proximity-checked visits are accepted for now.
        db.session.add(TagVisit(tag_point_id=tag_point.id, visitor_id=current_user.id, photo_image_id=image.id))
        _remember_location(current_user, lat, lon, now)
        db.session.commit()

        flash(t("flash.tag_logged"), "success")
        return redirect(url_for("tags.tag_detail", tag_id=tag_point.id))

    return render_template(
        "tag_log_upload.html", tag_point=tag_point, max_distance_meters=settings_service.get("log_visit_max_distance_meters")
    )


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
