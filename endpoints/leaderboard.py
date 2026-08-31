from flask import Blueprint, jsonify, render_template, request

from library.services.leaderboard_service import LeaderboardService
from library.services.settings_service import SettingsService

bp_leaderboard = Blueprint("leaderboard", __name__)
leaderboard_service = LeaderboardService()
settings_service = SettingsService()


@bp_leaderboard.route("/leaderboard")
def leaderboard_page():
    return render_template("leaderboard.html")


@bp_leaderboard.route("/api/leaderboard")
def leaderboard_api():
    scope = request.args.get("scope", "global")

    if scope == "national":
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        if lat is None or lon is None:
            return jsonify({"error": "no_location"}), 400
        nationality_code = leaderboard_service.country_code_from_location(lat, lon)
        if not nationality_code:
            return jsonify({"error": "no_nationality"}), 400
        territories = leaderboard_service.national_ranking(nationality_code)
    elif scope == "local":
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        if lat is None or lon is None:
            return jsonify({"error": "no_location"}), 400
        territories = leaderboard_service.local_ranking(
            lat, lon, radius_km=settings_service.get("local_leaderboard_radius_km")
        )
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
