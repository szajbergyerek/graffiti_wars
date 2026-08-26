from flask import Blueprint, render_template

from library.models.band import Band
from library.models.band_territory import BandTerritory
from library.models.news_feed_event import NewsFeedEvent
from library.models.tag_point import TagPoint
from library.models.user import User

bp_index = Blueprint("index", __name__)


@bp_index.route("/", methods=["GET"])
def index():
    band_count = Band.query.count()
    user_count = User.query.count()
    approved_tag_count = TagPoint.query.filter_by(status="approved").count()
    total_area_km2 = sum(territory.area_km2 for territory in BandTerritory.query.all())

    leaderboard = BandTerritory.query.order_by(BandTerritory.area_km2.desc()).limit(5).all()
    latest_events = NewsFeedEvent.query.order_by(NewsFeedEvent.created_at.desc()).limit(6).all()

    return render_template(
        "index.html",
        band_count=band_count,
        user_count=user_count,
        approved_tag_count=approved_tag_count,
        total_area_km2=round(total_area_km2, 2),
        leaderboard=leaderboard,
        latest_events=latest_events,
    )
