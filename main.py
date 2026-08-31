import logging
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, g, request
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix

from endpoints.admin import bp_admin
from endpoints.assets import bp_assets
from endpoints.auth import bp_auth
from endpoints.bands import bp_bands
from endpoints.chat import bp_chat
from endpoints.dev_capture import bp_dev_capture
from endpoints.feed import bp_feed
from endpoints.index import bp_index
from endpoints.leaderboard import bp_leaderboard
from endpoints.map_api import bp_map_api
from endpoints.profile import bp_profile
from endpoints.tags import bp_tags
from endpoints.tutorial import bp_tutorial
from library.config import Config
from library.extensions import csrf, db, login_manager, oauth
from library.i18n.countries import COUNTRY_BY_CODE
from library.services.color_utils import contrast_shade, hex_to_rgba
from library.services.translator import t, translator

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")


def create_app() -> Flask:
    """
    Build and configure the Flask application instance.

    :return: A fully configured Flask app, with the database schema ensured to exist.
    """
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    config = Config()
    app.config["SECRET_KEY"] = config.secret_key
    app.config["SQLALCHEMY_DATABASE_URI"] = config.database_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = config.max_content_length
    app.config["IMAGES_ROOT"] = config.images_root
    app.config["MODELS_ROOT"] = config.models_root
    # Static files (notably the ~12MB tag-detection model) default to a
    # revalidate-every-time cache policy, meaning a network round-trip on
    # every load even when the content hasn't changed. A day-long cache lets
    # a returning band member's browser skip that entirely.
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 86400
    # "Remember me" is not optional here - every login stays signed in until
    # an explicit logout, so both the underlying session and Flask-Login's
    # remember-me cookie need a long lifetime instead of the default
    # expire-when-the-browser-closes behavior.
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=365)
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=365)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    csrf.init_app(app)

    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=config.google_client_id,
        client_secret=config.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    app.jinja_env.globals["t"] = t
    app.jinja_env.globals["country_by_code"] = COUNTRY_BY_CODE
    app.jinja_env.globals["contrast_shade"] = contrast_shade
    app.jinja_env.globals["hex_to_rgba"] = hex_to_rgba

    @app.before_request
    def _resolve_locale():
        g.locale = translator.resolve_locale(request.accept_languages)

    @app.after_request
    def _set_security_headers(response):
        """
        Attach baseline security headers to every response.

        param response: The outgoing Flask response.

        :return: The same response, with the headers set.
        """
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        # Only meaningful once the browser has seen it over an actual HTTPS
        # connection, but harmless to always send - it primes future visits
        # even before HTTP->HTTPS redirection is set up at the proxy level.
        response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
        return response

    app.register_blueprint(bp_index)
    app.register_blueprint(bp_auth)
    app.register_blueprint(bp_bands)
    app.register_blueprint(bp_tags)
    app.register_blueprint(bp_map_api)
    app.register_blueprint(bp_profile)
    app.register_blueprint(bp_admin)
    app.register_blueprint(bp_assets)
    app.register_blueprint(bp_chat)
    app.register_blueprint(bp_dev_capture)
    app.register_blueprint(bp_feed)
    app.register_blueprint(bp_leaderboard)
    app.register_blueprint(bp_tutorial)

    with app.app_context():
        from library.models.admin_action import AdminAction
        from library.models.band import Band
        from library.models.band_join_request import BandJoinRequest
        from library.models.band_territory import BandTerritory
        from library.models.chat_message import ChatMessage
        from library.models.conversation import Conversation
        from library.models.conversation_participant import ConversationParticipant
        from library.models.image import Image
        from library.models.landmark import Landmark
        from library.models.news_feed_event import NewsFeedEvent
        from library.models.poll import Poll
        from library.models.poll_option import PollOption
        from library.models.poll_vote import PollVote
        from library.models.site_setting import SiteSetting
        from library.models.tag_comment import TagComment
        from library.models.tag_point import TagPoint
        from library.models.tag_report import TagReport
        from library.models.tag_visit import TagVisit
        from library.models.user import User
        from library.models.user_territory import UserTerritory

        db.create_all()

        # db.create_all() only creates tables that don't exist yet - it never
        # alters an existing table's columns. There's no migration tool in
        # this project, so new nullable columns are added this way instead,
        # idempotently, so both a fresh DB and an already-running one (e.g.
        # the production deployment) pick them up on next startup with no
        # manual step and no data loss.
        db.session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_location_lat DOUBLE PRECISION"))
        db.session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_location_lon DOUBLE PRECISION"))
        db.session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_location_at TIMESTAMP"))
        db.session.execute(
            text("ALTER TABLE bands ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE")
        )
        db.session.execute(text("ALTER TABLE bands ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP"))
        db.session.commit()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
