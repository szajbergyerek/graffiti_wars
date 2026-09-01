import json

from flask import Blueprint, jsonify, request
from sqlalchemy.orm import joinedload

from library.models.band_territory import BandTerritory
from library.models.tag_point import TagPoint
from library.models.tag_visit import TagVisit
from library.models.user_territory import UserTerritory

bp_map_api = Blueprint("map_api", __name__, url_prefix="/api")


def _parse_bbox(raw_bbox: str):
    """
    Parse a "west,south,east,north" query parameter into four floats.

    param raw_bbox: The raw `bbox` query string value, or None.

    :return: A (west, south, east, north) tuple, or None if missing/invalid.
    """
    if not raw_bbox:
        return None
    parts = raw_bbox.split(",")
    if len(parts) != 4:
        return None
    try:
        return tuple(float(part) for part in parts)
    except ValueError:
        return None


@bp_map_api.route("/territories.geojson")
def territories_geojson():
    query = BandTerritory.query.options(joinedload(BandTerritory.band))
    band_id = request.args.get("band_id", type=int)
    if band_id is not None:
        query = query.filter_by(band_id=band_id)

    features = []
    for territory in query.all():
        features.append(
            {
                "type": "Feature",
                "geometry": json.loads(territory.geojson),
                "properties": {
                    "band_id": territory.band_id,
                    "band_name": territory.band.name,
                    "color": territory.band.color,
                    "area_km2": round(territory.area_km2, 3),
                },
            }
        )
    return jsonify({"type": "FeatureCollection", "features": features})


@bp_map_api.route("/tags.geojson")
def tags_geojson():
    query = TagPoint.query.filter_by(status="approved").options(
        joinedload(TagPoint.band), joinedload(TagPoint.photo_image), joinedload(TagPoint.submitted_by)
    )

    bbox = _parse_bbox(request.args.get("bbox"))
    if bbox is not None:
        west, south, east, north = bbox
        query = query.filter(
            TagPoint.lon >= west, TagPoint.lon <= east, TagPoint.lat >= south, TagPoint.lat <= north
        )

    band_id = request.args.get("band_id", type=int)
    if band_id is not None:
        query = query.filter(TagPoint.band_id == band_id)

    user_id = request.args.get("user_id", type=int)
    if user_id is not None:
        query = query.filter(TagPoint.submitted_by_id == user_id)

    features = []
    for point in query.all():
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [point.lon, point.lat]},
                "properties": {
                    "id": point.id,
                    "band_id": point.band_id,
                    "band_name": point.band.name if point.band else None,
                    "color": point.band.color if point.band else point.submitted_by.color,
                    "photo_url": point.photo_image.url if point.photo_image else None,
                    "created_at": point.created_at.isoformat(),
                    "submitted_by": point.submitted_by.username,
                    "submitted_by_id": point.submitted_by_id,
                },
            }
        )
    return jsonify({"type": "FeatureCollection", "features": features})


@bp_map_api.route("/user-territories.geojson")
def user_territories_geojson():
    query = UserTerritory.query.options(joinedload(UserTerritory.user))
    user_id = request.args.get("user_id", type=int)
    if user_id is not None:
        query = query.filter_by(user_id=user_id)

    features = []
    for territory in query.all():
        features.append(
            {
                "type": "Feature",
                "geometry": json.loads(territory.geojson),
                "properties": {
                    "user_id": territory.user_id,
                    "username": territory.user.username,
                    "color": territory.user.color,
                    "area_km2": round(territory.area_km2, 3),
                },
            }
        )
    return jsonify({"type": "FeatureCollection", "features": features})


@bp_map_api.route("/visited-tags.geojson")
def visited_tags_geojson():
    user_id = request.args.get("user_id", type=int)
    if user_id is None:
        return jsonify({"type": "FeatureCollection", "features": []})

    visits = TagVisit.query.filter_by(visitor_id=user_id).options(
        joinedload(TagVisit.tag_point).joinedload(TagPoint.band),
        joinedload(TagVisit.tag_point).joinedload(TagPoint.submitted_by),
    )

    features = []
    for visit in visits:
        point = visit.tag_point
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [point.lon, point.lat]},
                "properties": {
                    "id": point.id,
                    "band_name": point.band.name if point.band else None,
                    "color": point.band.color if point.band else point.submitted_by.color,
                    "submitted_by": point.submitted_by.username,
                },
            }
        )
    return jsonify({"type": "FeatureCollection", "features": features})
