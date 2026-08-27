import json
import math
from typing import List

from shapely.geometry import shape
from sqlalchemy.orm import joinedload, selectinload

from library.models.band import Band
from library.models.band_territory import BandTerritory

EARTH_RADIUS_KM = 6371.0
DEFAULT_LOCAL_RADIUS_KM = 25.0


class LeaderboardService:
    """
    Ranks bands by territory size, optionally scoped to a nationality
    ("national") or a physical radius around a point ("local"). A band with
    no approved tags yet has no territory and so cannot appear in a
    national or local ranking, since there is no location to test it against.
    """

    def _base_query(self):
        return BandTerritory.query.options(joinedload(BandTerritory.band).selectinload(Band.members))

    def global_ranking(self) -> List[BandTerritory]:
        """
        Rank every band by territory size, largest first.

        :return: BandTerritory rows sorted by area descending.
        """
        return self._base_query().order_by(BandTerritory.area_km2.desc()).all()

    def national_ranking(self, nationality_code: str) -> List[BandTerritory]:
        """
        Rank bands that share the given nationality, largest first.

        param nationality_code: The ISO 3166-1 alpha-2 code to filter bands by.

        :return: Matching BandTerritory rows sorted by area descending.
        """
        return (
            self._base_query()
            .join(Band, BandTerritory.band_id == Band.id)
            .filter(Band.nationality_code == nationality_code)
            .order_by(BandTerritory.area_km2.desc())
            .all()
        )

    def local_ranking(self, lat: float, lon: float, radius_km: float = DEFAULT_LOCAL_RADIUS_KM) -> List[BandTerritory]:
        """
        Rank bands whose territory centroid is within `radius_km` of a point, largest first.

        param lat: Latitude of the reference point (e.g. the viewer's browser geolocation).
        param lon: Longitude of the reference point.
        param radius_km: Maximum distance from the reference point, in kilometers.

        :return: Matching BandTerritory rows sorted by area descending.
        """
        nearby = []
        for territory in self._base_query().all():
            centroid = shape(json.loads(territory.geojson)).centroid
            if self._haversine_km(lat, lon, centroid.y, centroid.x) <= radius_km:
                nearby.append(territory)
        nearby.sort(key=lambda t: t.area_km2, reverse=True)
        return nearby

    def _haversine_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))
