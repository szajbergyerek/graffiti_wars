import json

from flask import Blueprint, jsonify, request

from library.models.band_territory import BandTerritory
from library.models.tag_point import TagPoint

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
    features = []
    for territory in BandTerritory.query.all():
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
    query = TagPoint.query.filter_by(status="approved")

    bbox = _parse_bbox(request.args.get("bbox"))
    if bbox is not None:
        west, south, east, north = bbox
        query = query.filter(
            TagPoint.lon >= west, TagPoint.lon <= east, TagPoint.lat >= south, TagPoint.lat <= north
        )

    features = []
    for point in query.all():
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [point.lon, point.lat]},
                "properties": {
                    "id": point.id,
                    "band_id": point.band_id,
                    "band_name": point.band.name,
                    "color": point.band.color,
                    "photo_url": point.photo_image.url if point.photo_image else None,
                    "created_at": point.created_at.isoformat(),
                },
            }
        )
    return jsonify({"type": "FeatureCollection", "features": features})
