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
    entity = request.args.get("entity", "band")
    is_band = entity != "individual"

    if scope == "national":
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        if lat is None or lon is None:
            return jsonify({"error": "no_location"}), 400
        nationality_code = leaderboard_service.country_code_from_location(lat, lon)
        if not nationality_code:
            return jsonify({"error": "no_nationality"}), 400
        rows = (
            leaderboard_service.national_band_ranking(nationality_code)
            if is_band
            else leaderboard_service.national_user_ranking(nationality_code)
        )
    elif scope == "local":
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        if lat is None or lon is None:
            return jsonify({"error": "no_location"}), 400
        radius_km = settings_service.get("local_leaderboard_radius_km")
        rows = (
            leaderboard_service.local_band_ranking(lat, lon, radius_km=radius_km)
            if is_band
            else leaderboard_service.local_user_ranking(lat, lon, radius_km=radius_km)
        )
    else:
        rows = leaderboard_service.global_band_ranking() if is_band else leaderboard_service.global_user_ranking()

    offset = request.args.get("offset", type=int, default=0)
    limit = min(request.args.get("limit", type=int, default=10), 50)
    page = rows[offset : offset + limit]

    if is_band:
        return jsonify(
            [
                {
                    "band_id": row.band.id,
                    "band_name": row.band.name,
                    "color": row.band.color,
                    "tag_count": row.tag_count,
                    "area_km2": round(row.territory.area_km2, 3) if row.territory else 0,
                    "member_count": len(row.band.members),
                }
                for row in page
            ]
        )

    return jsonify(
        [
            {
                "user_id": row.user.id,
                "username": row.user.username,
                "avatar_url": row.user.display_avatar_url,
                "tag_count": row.tag_count,
                "area_km2": round(row.territory.area_km2, 3) if row.territory else 0,
                "band_name": row.user.band.name if row.user.band else None,
            }
            for row in page
        ]
    )
