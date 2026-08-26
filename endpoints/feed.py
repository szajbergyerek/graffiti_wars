from flask import Blueprint, render_template

from library.models.news_feed_event import NewsFeedEvent

bp_feed = Blueprint("feed", __name__)


@bp_feed.route("/feed")
def feed():
    events = NewsFeedEvent.query.order_by(NewsFeedEvent.created_at.desc()).limit(50).all()
    return render_template("feed.html", events=events)
