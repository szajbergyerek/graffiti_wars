from flask import Blueprint, jsonify, render_template, request

from library.models.news_feed_event import NewsFeedEvent

bp_feed = Blueprint("feed", __name__)


@bp_feed.route("/feed")
def feed():
    return render_template("feed.html")


@bp_feed.route("/api/feed")
def feed_api():
    offset = request.args.get("offset", type=int, default=0)
    limit = min(request.args.get("limit", type=int, default=10), 50)

    events = (
        NewsFeedEvent.query.order_by(NewsFeedEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return jsonify(
        [
            {
                "message": event.message,
                "created_at": event.created_at.strftime("%Y.%m.%d %H:%M"),
                "color": event.band.color if event.band else None,
            }
            for event in events
        ]
    )
