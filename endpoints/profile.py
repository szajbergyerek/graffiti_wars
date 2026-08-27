from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from library.extensions import db
from library.i18n.countries import COUNTRIES, COUNTRY_BY_CODE
from library.models.tag_point import TagPoint
from library.models.user import User
from library.services.image_storage import ImageStorage
from library.services.translator import t
from library.services.username_validator import UsernameValidator

bp_profile = Blueprint("profile", __name__)
username_validator = UsernameValidator()


def _build_profile_context(user: User) -> dict:
    submitted = TagPoint.query.filter_by(submitted_by_id=user.id).count()
    approved = TagPoint.query.filter_by(submitted_by_id=user.id, status="approved").count()

    contribution_percent = 0.0
    if user.band_id:
        band_total = TagPoint.query.filter_by(band_id=user.band_id, status="approved").count()
        if band_total:
            contribution_percent = round((approved / band_total) * 100, 1)

    recent_tags = (
        TagPoint.query.filter_by(submitted_by_id=user.id).order_by(TagPoint.created_at.desc()).limit(6).all()
    )

    return {
        "profile_user": user,
        "submitted": submitted,
        "approved": approved,
        "contribution_percent": contribution_percent,
        "recent_tags": recent_tags,
    }


@bp_profile.route("/profile")
def my_profile():
    if not current_user.is_authenticated:
        return render_template("profile.html", is_own_profile=True)
    return render_template("profile.html", is_own_profile=True, **_build_profile_context(current_user))


@bp_profile.route("/users/<username>")
def user_profile(username: str):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    return render_template("profile.html", is_own_profile=False, **_build_profile_context(user))


@bp_profile.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        username = username_validator.normalize(request.form.get("username", current_user.username))
        bio = request.form.get("bio", "").strip()[:300]
        nationality_code = request.form.get("nationality_code") or None
        if nationality_code and nationality_code not in COUNTRY_BY_CODE:
            nationality_code = None

        if username != current_user.username:
            username_error = username_validator.validate(username)
            if username_error:
                flash(t(username_error), "error")
                return render_template("profile_edit.html", countries=COUNTRIES)
            if User.query.filter(User.username == username, User.id != current_user.id).first():
                flash(t("flash.username_taken"), "error")
                return render_template("profile_edit.html", countries=COUNTRIES)
            current_user.username = username

        storage = ImageStorage(current_app.config["IMAGES_ROOT"])

        avatar_file = request.files.get("avatar")
        if avatar_file and avatar_file.filename:
            try:
                image = storage.save(avatar_file, "avatars", uploaded_by_id=current_user.id)
            except ValueError:
                flash(t("flash.unsupported_image"), "error")
                return render_template("profile_edit.html", countries=COUNTRIES)
            current_user.avatar_image_id = image.id

        banner_file = request.files.get("banner")
        if banner_file and banner_file.filename:
            try:
                image = storage.save(banner_file, "banners", uploaded_by_id=current_user.id)
            except ValueError:
                flash(t("flash.unsupported_image"), "error")
                return render_template("profile_edit.html", countries=COUNTRIES)
            current_user.banner_image_id = image.id

        current_user.bio = bio
        current_user.nationality_code = nationality_code
        current_user.allow_direct_messages = request.form.get("allow_direct_messages") == "on"
        db.session.commit()

        flash(t("flash.profile_updated"), "success")
        return redirect(url_for("profile.my_profile"))

    return render_template("profile_edit.html", countries=COUNTRIES)
