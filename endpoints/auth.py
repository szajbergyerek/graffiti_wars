from flask import Blueprint, flash, redirect, url_for
from flask_login import login_required, login_user, logout_user

from library.extensions import db, login_manager, oauth
from library.models.user import User
from library.services.translator import t
from library.services.username_validator import UsernameValidator

bp_auth = Blueprint("auth", __name__)
username_validator = UsernameValidator()


@login_manager.user_loader
def load_user(user_id: str):
    """
    Load a user by primary key for Flask-Login's session handling.

    param user_id: The user id stored in the session, as a string.

    :return: The matching User, or None.
    """
    return db.session.get(User, int(user_id))


def _unique_username(base_username: str) -> str:
    """
    Make sure a candidate username doesn't collide with an existing one,
    appending a numeric suffix (and trimming to fit the length limit) until it does not.

    param base_username: The already-valid candidate username.

    :return: A username guaranteed to be free in the database.
    """
    candidate = base_username
    suffix = 1
    while User.query.filter_by(username=candidate).first() is not None:
        suffix += 1
        marker = f"_{suffix}"
        candidate = f"{base_username[: UsernameValidator.MAX_LENGTH - len(marker)]}{marker}"
    return candidate


def _find_or_create_user(google_id: str, email: str, name: str, picture: str) -> tuple[User, bool]:
    """
    Look up a user by their Google account, or create one on first login.

    param google_id: The stable Google account identifier ("sub" claim).
    param email: The Google account's email address.
    param name: The Google account's display name, used to derive a username for new accounts.
    param picture: The Google account's profile picture URL, used only for new accounts -
        existing users may have replaced it with their own uploaded avatar since.

    :return: A tuple of (user, is_newly_created).
    """
    user = User.query.filter_by(google_id=google_id).first()
    if user is not None:
        return user, False

    user = User.query.filter_by(email=email).first()
    if user is not None:
        user.google_id = google_id
        return user, False

    username = username_validator.derive_from_display_name(name, fallback=email.split("@")[0])
    username = _unique_username(username)

    user = User(
        username=username,
        email=email,
        google_id=google_id,
        avatar_seed=username,
        avatar_url=picture,
    )
    db.session.add(user)
    return user, True


@bp_auth.route("/login")
def login():
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@bp_auth.route("/auth/google/callback")
def google_callback():
    token = oauth.google.authorize_access_token()
    userinfo = token.get("userinfo")

    user, is_new_user = _find_or_create_user(
        google_id=userinfo["sub"],
        email=userinfo["email"],
        name=userinfo.get("name", ""),
        picture=userinfo.get("picture"),
    )
    db.session.commit()

    if user.is_banned:
        flash(t("flash.account_banned"), "error")
        return redirect(url_for("index.index"))

    login_user(user)
    if is_new_user:
        return redirect(url_for("profile.my_profile"))
    return redirect(url_for("tags.map_view"))


@bp_auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index.index"))
