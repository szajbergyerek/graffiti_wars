import logging

from dotenv import load_dotenv
from flask import Flask, g, request

from endpoints.admin import bp_admin
from endpoints.assets import bp_assets
from endpoints.auth import bp_auth
from endpoints.bands import bp_bands
from endpoints.chat import bp_chat
from endpoints.feed import bp_feed
from endpoints.index import bp_index
from endpoints.leaderboard import bp_leaderboard
from endpoints.map_api import bp_map_api
from endpoints.profile import bp_profile
from endpoints.tags import bp_tags
from library.config import Config
from library.extensions import db, login_manager, oauth
from library.i18n.countries import COUNTRY_BY_CODE
from library.services.translator import t, translator

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")


def create_app() -> Flask:
    """
    Build and configure the Flask application instance.

    :return: A fully configured Flask app, with the database schema ensured to exist.
    """
    app = Flask(__name__)
    config = Config()
    app.config["SECRET_KEY"] = config.secret_key
    app.config["SQLALCHEMY_DATABASE_URI"] = config.database_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = config.max_content_length
    app.config["TAG_RADIUS_METERS"] = config.tag_radius_meters
    app.config["IMAGES_ROOT"] = config.images_root

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

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

    def _unread_chat_count() -> int:
        from flask_login import current_user

        if not current_user.is_authenticated:
            return 0
        from library.services.chat_service import ChatService

        return ChatService().unread_count(current_user)

    app.jinja_env.globals["unread_chat_count"] = _unread_chat_count

    @app.before_request
    def _resolve_locale():
        g.locale = translator.resolve_locale(request.accept_languages)

    app.register_blueprint(bp_index)
    app.register_blueprint(bp_auth)
    app.register_blueprint(bp_bands)
    app.register_blueprint(bp_tags)
    app.register_blueprint(bp_map_api)
    app.register_blueprint(bp_profile)
    app.register_blueprint(bp_admin)
    app.register_blueprint(bp_assets)
    app.register_blueprint(bp_chat)
    app.register_blueprint(bp_feed)
    app.register_blueprint(bp_leaderboard)

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
        from library.models.tag_comment import TagComment
        from library.models.tag_like import TagLike
        from library.models.tag_point import TagPoint
        from library.models.tag_report import TagReport
        from library.models.user import User

        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
