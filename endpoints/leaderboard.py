from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user

from library.services.leaderboard_service import LeaderboardService

bp_leaderboard = Blueprint("leaderboard", __name__)
leaderboard_service = LeaderboardService()


@bp_leaderboard.route("/leaderboard")
def leaderboard_page():
    return render_template("leaderboard.html")


@bp_leaderboard.route("/api/leaderboard")
def leaderboard_api():
    scope = request.args.get("scope", "global")

    if scope == "national":
        nationality_code = request.args.get("nationality")
        if not nationality_code and current_user.is_authenticated:
            nationality_code = current_user.nationality_code
        if not nationality_code:
            return jsonify({"error": "no_nationality"}), 400
        territories = leaderboard_service.national_ranking(nationality_code)
    elif scope == "local":
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        if lat is None or lon is None:
            return jsonify({"error": "no_location"}), 400
        territories = leaderboard_service.local_ranking(lat, lon)
    else:
        territories = leaderboard_service.global_ranking()

    offset = request.args.get("offset", type=int, default=0)
    limit = min(request.args.get("limit", type=int, default=10), 50)
    page = territories[offset : offset + limit]

    return jsonify(
        [
            {
                "band_id": territory.band_id,
                "band_name": territory.band.name,
                "color": territory.band.color,
                "area_km2": round(territory.area_km2, 3),
                "member_count": len(territory.band.members),
            }
            for territory in page
        ]
    )
