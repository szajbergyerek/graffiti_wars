from datetime import datetime

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from library.extensions import db
from library.i18n.countries import COUNTRIES, COUNTRY_BY_CODE
from library.models.band import JOIN_POLICIES, Band
from library.models.band_join_request import BandJoinRequest
from library.models.band_territory import BandTerritory
from library.models.landmark import LANDMARK_CATEGORIES, Landmark
from library.models.news_feed_event import NewsFeedEvent
from library.models.tag_point import TagPoint
from library.models.user import User
from library.services.chat_service import ChatService
from library.services.image_storage import ImageStorage
from library.services.leaderboard_service import LeaderboardService
from library.services.translator import t
from library.services.username_validator import UsernameValidator

bp_bands = Blueprint("bands", __name__, url_prefix="/bands")
chat_service = ChatService()
username_validator = UsernameValidator()
leaderboard_service = LeaderboardService()


@bp_bands.route("/")
def list_bands():
    query_text = request.args.get("q", "").strip()
    sort_key = request.args.get("sort", "newest")
    scope = request.args.get("scope", "global")
    join_policy_filter = request.args.get("join_policy", "all")

    bands = Band.query

    if query_text:
        bands = bands.filter(Band.name.ilike(f"%{query_text}%"))
    if join_policy_filter in JOIN_POLICIES:
        bands = bands.filter(Band.join_policy == join_policy_filter)

    bands = bands.all()

    if scope == "national":
        nationality_code = current_user.nationality_code if current_user.is_authenticated else None
        bands = [band for band in bands if nationality_code and band.nationality_code == nationality_code]
    elif scope == "local":
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        if lat is not None and lon is not None:
            local_band_ids = {t.band_id for t in leaderboard_service.local_ranking(lat, lon)}
            bands = [band for band in bands if band.id in local_band_ids]
        else:
            bands = []

    if sort_key == "oldest":
        bands.sort(key=lambda band: band.created_at)
    elif sort_key == "area":
        bands.sort(key=lambda band: band.territory.area_km2 if band.territory else 0, reverse=True)
    elif sort_key == "members":
        bands.sort(key=lambda band: len(band.members), reverse=True)
    else:
        bands.sort(key=lambda band: band.created_at, reverse=True)

    return render_template(
        "band_list.html",
        bands=bands,
        query_text=query_text,
        sort_key=sort_key,
        scope=scope,
        join_policy_filter=join_policy_filter,
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
        reference_image = request.files.get("reference_image")

        if not name or reference_image is None or reference_image.filename == "":
            flash(t("flash.band_missing_fields"), "error")
            return render_template("band_create.html")

        if Band.query.filter_by(name=name).first():
            flash(t("flash.band_name_taken"), "error")
            return render_template("band_create.html")

        storage = ImageStorage(current_app.config["IMAGES_ROOT"])
        try:
            image = storage.save(reference_image, "tags", uploaded_by_id=current_user.id)
        except ValueError:
            flash(t("flash.unsupported_image"), "error")
            return render_template("band_create.html")

        band = Band(
            name=name,
            description=description,
            reference_image_id=image.id,
            color=Band.next_color(Band.query.count()),
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

    return render_template("band_create.html")


@bp_bands.route("/<int:band_id>")
def band_detail(band_id: int):
    band = Band.query.get_or_404(band_id)
    members = User.query.filter_by(band_id=band.id).order_by(User.band_joined_at.asc()).all()

    approved_counts = {
        member.id: TagPoint.query.filter_by(band_id=band.id, submitted_by_id=member.id, status="approved").count()
        for member in members
    }
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

    landmarks_by_category = {}
    for landmark in Landmark.query.filter_by(band_id=band.id).all():
        landmarks_by_category.setdefault(landmark.category, []).append(landmark)

    return render_template(
        "band_detail.html",
        band=band,
        members=members,
        approved_counts=approved_counts,
        total_approved=total_approved,
        territory=territory,
        is_leader=is_leader,
        own_pending_request=own_pending_request,
        pending_requests=pending_requests,
        landmark_categories=LANDMARK_CATEGORIES,
        landmarks_by_category=landmarks_by_category,
    )


@bp_bands.route("/<int:band_id>/join", methods=["POST"])
@login_required
def join_band(band_id: int):
    band = Band.query.get_or_404(band_id)
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
    db.session.commit()

    flash(t("flash.member_kicked", username=member.username), "success")
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
    db.session.commit()

    flash(t("flash.left_band"), "success")
    return redirect(url_for("index.index"))
