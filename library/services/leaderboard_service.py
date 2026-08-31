import json
import math
from typing import List, Optional

import requests
from shapely.geometry import shape
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

from library.extensions import db
from library.models.band import Band
from library.models.band_territory import BandTerritory
from library.models.tag_point import TagPoint
from library.models.user import User
from library.models.user_territory import UserTerritory

EARTH_RADIUS_KM = 6371.0
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_HEADERS = {"User-Agent": "GraffitiWars/1.0 (contact: graffitiwars app)"}


class BandRankingRow:
    """One band's position in a tag-count leaderboard, paired with its (purely visual) territory."""

    def __init__(self, band: Band, tag_count: int, territory: Optional[BandTerritory]) -> None:
        self.band = band
        self.tag_count = tag_count
        self.territory = territory


class UserRankingRow:
    """One user's position in a tag-count leaderboard, paired with their (purely visual) territory."""

    def __init__(self, user: User, tag_count: int, territory: Optional[UserTerritory]) -> None:
        self.user = user
        self.tag_count = tag_count
        self.territory = territory


class LeaderboardService:
    """
    Ranks bands and individual users by how many approved tags they have,
    optionally scoped to a nationality ("national") or a physical radius
    around a point ("local"). Territory size is no longer part of the
    ranking - it is still computed (see TerritoryEngine) purely for the map
    and profile display. A band/user with no approved tags yet has no
    location to test against and so cannot appear in a national or local
    ranking.
    """

    def _band_tag_counts(self):
        return dict(
            db.session.query(TagPoint.band_id, func.count(TagPoint.id))
            .filter(TagPoint.status == "approved")
            .group_by(TagPoint.band_id)
            .all()
        )

    def _user_tag_counts(self):
        return dict(
            db.session.query(TagPoint.submitted_by_id, func.count(TagPoint.id))
            .filter(TagPoint.status == "approved")
            .group_by(TagPoint.submitted_by_id)
            .all()
        )

    def global_band_ranking(self) -> List[BandRankingRow]:
        """
        Rank every band with at least one approved tag by tag count, most first.

        :return: BandRankingRow list sorted by tag count descending.
        """
        counts = self._band_tag_counts()
        bands = (
            Band.query.filter(Band.is_deleted.is_(False), Band.id.in_(counts.keys()))
            .options(joinedload(Band.territory), selectinload(Band.members))
            .all()
        )
        rows = [BandRankingRow(band, counts[band.id], band.territory) for band in bands]
        rows.sort(key=lambda row: row.tag_count, reverse=True)
        return rows

    def global_user_ranking(self) -> List[UserRankingRow]:
        """
        Rank every user with at least one approved tag by tag count, most first.

        :return: UserRankingRow list sorted by tag count descending.
        """
        counts = self._user_tag_counts()
        users = (
            User.query.filter(User.id.in_(counts.keys())).options(joinedload(User.territory)).all()
        )
        rows = [UserRankingRow(user, counts[user.id], user.territory) for user in users]
        rows.sort(key=lambda row: row.tag_count, reverse=True)
        return rows

    def country_code_from_location(self, lat: float, lon: float) -> Optional[str]:
        """
        Reverse-geocode a point to the ISO 3166-1 alpha-2 code of the country
        it currently falls in, using the public Nominatim (OpenStreetMap) API.

        param lat: Latitude of the point (e.g. the viewer's current browser geolocation).
        param lon: Longitude of the point.

        :return: The uppercase country code, or None if it couldn't be resolved.
        """
        try:
            response = requests.get(
                NOMINATIM_REVERSE_URL,
                params={"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 3},
                timeout=5,
                headers=NOMINATIM_HEADERS,
            )
            response.raise_for_status()
            country_code = response.json().get("address", {}).get("country_code")
        except (requests.RequestException, ValueError):
            return None
        return country_code.upper() if country_code else None

    def national_band_ranking(self, nationality_code: str) -> List[BandRankingRow]:
        """
        Rank bands that share the given nationality by tag count, most first.

        param nationality_code: The ISO 3166-1 alpha-2 code to filter bands by.

        :return: Matching BandRankingRow list sorted by tag count descending.
        """
        return [row for row in self.global_band_ranking() if row.band.nationality_code == nationality_code]

    def national_user_ranking(self, nationality_code: str) -> List[UserRankingRow]:
        """
        Rank users whose live location resolved to the given nationality by tag count, most first.

        param nationality_code: The ISO 3166-1 alpha-2 code to filter users by.

        :return: Matching UserRankingRow list sorted by tag count descending.
        """
        return [row for row in self.global_user_ranking() if row.user.nationality_code == nationality_code]

    def local_band_ranking(self, lat: float, lon: float, radius_km: float) -> List[BandRankingRow]:
        """
        Rank bands whose territory centroid is within `radius_km` of a point, by tag count, most first.

        param lat: Latitude of the reference point (e.g. the viewer's browser geolocation).
        param lon: Longitude of the reference point.
        param radius_km: Maximum distance from the reference point, in kilometers.

        :return: Matching BandRankingRow list sorted by tag count descending.
        """
        nearby = []
        for row in self.global_band_ranking():
            if row.territory is None:
                continue
            centroid = shape(json.loads(row.territory.geojson)).centroid
            if self._haversine_km(lat, lon, centroid.y, centroid.x) <= radius_km:
                nearby.append(row)
        return nearby

    def local_user_ranking(self, lat: float, lon: float, radius_km: float) -> List[UserRankingRow]:
        """
        Rank users whose territory centroid is within `radius_km` of a point, by tag count, most first.

        param lat: Latitude of the reference point (e.g. the viewer's browser geolocation).
        param lon: Longitude of the reference point.
        param radius_km: Maximum distance from the reference point, in kilometers.

        :return: Matching UserRankingRow list sorted by tag count descending.
        """
        nearby = []
        for row in self.global_user_ranking():
            if row.territory is None:
                continue
            centroid = shape(json.loads(row.territory.geojson)).centroid
            if self._haversine_km(lat, lon, centroid.y, centroid.x) <= radius_km:
                nearby.append(row)
        return nearby

    def _haversine_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))
