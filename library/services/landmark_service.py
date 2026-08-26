import json
import logging
from typing import List

import requests
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from library.extensions import db
from library.models.band import Band
from library.models.landmark import LANDMARK_CATEGORIES, Landmark

logger = logging.getLogger("landmark_service")

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_TIMEOUT_SECONDS = 25
OVERPASS_HEADERS = {"User-Agent": "GraffitiWars/1.0 (contact: graffitiwars app)"}


class LandmarkService:
    """
    Counts OpenStreetMap points of interest (amenities, shops, tourism spots,
    leisure facilities, historic sites, offices) that fall inside a band's
    current territory, using the public Overpass API. Results are cached in
    the `landmarks` table and only refreshed on request (typically right
    after a band's territory changes), since a live Overpass query can take
    several seconds and the public instance is rate-limited.
    """

    def refresh_for_band(self, band: Band) -> bool:
        """
        Re-fetch every landmark inside a band's current territory and replace the cached rows.

        param band: The band whose territory should be scanned. If it has no territory yet, this just clears old rows.

        :return: True if the refresh completed (even with zero results), False if the Overpass request failed.
        """
        Landmark.query.filter_by(band_id=band.id).delete()

        if band.territory is None:
            db.session.commit()
            return True

        geometry = shape(json.loads(band.territory.geojson))
        polygons = list(geometry.geoms) if geometry.geom_type == "MultiPolygon" else [geometry]

        query = self._build_query(polygons)
        try:
            response = requests.post(
                OVERPASS_URL, data={"data": query}, timeout=OVERPASS_TIMEOUT_SECONDS, headers=OVERPASS_HEADERS
            )
            response.raise_for_status()
            elements = response.json().get("elements", [])
        except (requests.RequestException, ValueError) as error:
            logger.warning("Overpass query failed for band %s: %s", band.id, error)
            db.session.rollback()
            return False

        seen_osm_ids = set()
        for element in elements:
            osm_id = f"{element.get('type')}/{element.get('id')}"
            if osm_id in seen_osm_ids:
                continue
            seen_osm_ids.add(osm_id)

            tags = element.get("tags", {})
            category = next((c for c in LANDMARK_CATEGORIES if c in tags), None)
            if category is None:
                continue

            lat = element.get("lat")
            lon = element.get("lon")
            if lat is None or lon is None:
                center = element.get("center", {})
                lat, lon = center.get("lat"), center.get("lon")
            if lat is None or lon is None:
                continue

            db.session.add(
                Landmark(
                    band_id=band.id,
                    osm_id=osm_id,
                    category=category,
                    subtype=tags.get(category),
                    name=tags.get("name"),
                    lat=lat,
                    lon=lon,
                )
            )

        db.session.commit()
        logger.info("Refreshed %s landmarks for band %s", len(seen_osm_ids), band.id)
        return True

    def _build_query(self, polygons: List[BaseGeometry]) -> str:
        clauses = []
        for polygon in polygons:
            poly_filter = " ".join(f"{lat} {lon}" for lon, lat in polygon.exterior.coords)
            for category in LANDMARK_CATEGORIES:
                clauses.append(f'nwr["{category}"](poly:"{poly_filter}");')

        body = "\n  ".join(clauses)
        return f'[out:json][timeout:{OVERPASS_TIMEOUT_SECONDS}];\n(\n  {body}\n);\nout center tags;'
