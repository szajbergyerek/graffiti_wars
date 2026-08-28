from flask import Blueprint, jsonify, render_template, request
from sqlalchemy.orm import joinedload

from library.models.tag_point import TagPoint

bp_feed = Blueprint("feed", __name__)


@bp_feed.route("/feed")
def feed():
    return render_template("feed.html")


@bp_feed.route("/api/feed")
def feed_api():
    offset = request.args.get("offset", type=int, default=0)
    limit = min(request.args.get("limit", type=int, default=10), 50)

    tag_points = (
        TagPoint.query.filter_by(status="approved")
        .options(joinedload(TagPoint.submitted_by), joinedload(TagPoint.band), joinedload(TagPoint.photo_image))
        .order_by(TagPoint.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return jsonify(
        [
            {
                "id": tag_point.id,
                "photo_url": tag_point.photo_image.url,
                "username": tag_point.submitted_by.username,
                "avatar_url": tag_point.submitted_by.display_avatar_url,
                "band_name": tag_point.band.name,
                "band_color": tag_point.band.color,
                "lat": tag_point.lat,
                "lon": tag_point.lon,
                "created_at": tag_point.created_at.strftime("%Y.%m.%d %H:%M"),
            }
            for tag_point in tag_points
        ]
    )
