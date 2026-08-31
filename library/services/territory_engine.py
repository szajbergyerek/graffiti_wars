import json
from typing import Dict, List

from shapely.geometry import Point, Polygon, mapping
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from library.extensions import db
from library.models.band_territory import BandTerritory
from library.models.tag_point import TagPoint
from library.models.user_territory import UserTerritory
from library.services.geo_projector import GeoProjector


class TerritoryEngine:
    """
    Recomputes every band's and every user's territory from scratch.

    Tags are grouped into spatial clusters: two tags belong to the same
    cluster if they are within `cluster_link_distance` of each other
    (chained transitively, so a "necklace" of nearby tags all merge into one
    group even if the two ends are farther apart than the threshold). Each
    cluster's claim is the convex hull of its own (buffered) tags, so the
    "attraction zone" between tags in the same neighborhood is filled in -
    but a tag on the other side of the map starts its own separate cluster
    instead of dragging a claimed corridor across everything in between.

    This is a non-competitive game: territory is never taken away from
    anyone. A band's territory is simply the union of its own clusters, and
    a user's personal territory is simply the union of their own clusters -
    two different owners' territory can freely overlap on the map, nothing
    is carved out of it by anyone else's tags.
    """

    def __init__(self, radius_meters: float = 100.0, cluster_link_multiplier: float = 4.0) -> None:
        self.radius_meters = radius_meters
        self.cluster_link_distance = radius_meters * cluster_link_multiplier

    @classmethod
    def from_settings(cls) -> "TerritoryEngine":
        """
        Build a TerritoryEngine using the admin-configured `tag_radius_meters`
        and `cluster_link_multiplier` settings, instead of the class defaults.

        :return: A TerritoryEngine ready to call recompute_all() on.
        """
        from library.services.settings_service import SettingsService

        settings = SettingsService()
        return cls(
            radius_meters=settings.get("tag_radius_meters"),
            cluster_link_multiplier=settings.get("cluster_link_multiplier"),
        )

    def recompute_all(self) -> None:
        """
        Recompute and persist every band's and every user's territory
        polygon from the current set of approved tag points, replacing
        whatever was stored before. Each point's own contribution to its
        cluster's hull growth is cached on the point at the same time, so
        tag detail pages can read it directly instead of re-running the
        clustering live.

        :return: None
        """
        points = (
            TagPoint.query.filter_by(status="approved")
            .order_by(TagPoint.created_at.asc(), TagPoint.id.asc())
            .all()
        )

        BandTerritory.query.delete()
        UserTerritory.query.delete()

        if not points:
            db.session.commit()
            return

        center_lat = sum(p.lat for p in points) / len(points)
        center_lon = sum(p.lon for p in points) / len(points)
        projector = GeoProjector(center_lat, center_lon)
        projected = {point.id: projector.to_meters(Point(point.lon, point.lat)) for point in points}

        band_geometries, point_area_added = self._grouped_geometries(
            points, projected, group_key=lambda point: point.band_id
        )
        for band_id, (geometry, area_km2) in band_geometries.items():
            db.session.add(
                BandTerritory(band_id=band_id, geojson=json.dumps(mapping(projector.to_wgs84(geometry))), area_km2=area_km2)
            )

        user_geometries, _ = self._grouped_geometries(
            points, projected, group_key=lambda point: point.submitted_by_id
        )
        for user_id, (geometry, area_km2) in user_geometries.items():
            db.session.add(
                UserTerritory(user_id=user_id, geojson=json.dumps(mapping(projector.to_wgs84(geometry))), area_km2=area_km2)
            )

        for point in points:
            point.area_added_km2 = point_area_added.get(point.id, 0.0)

        db.session.commit()

    def _grouped_geometries(self, points: List[TagPoint], projected: Dict[int, Point], group_key) -> tuple:
        """
        Cluster an arbitrary set of approved tag points by an owner key
        (band id or submitting user id) and compute each owner's territory
        as the union of its own clusters' convex hulls, in chronological order.

        param points: Approved tag points, in chronological order.
        param projected: Each tag point's location, projected to meters, keyed by tag point id.
        param group_key: A function mapping a TagPoint to the owner id its territory should count towards.

        :return: An (owner_geometries, point_area_added) tuple - owner_geometries maps
            owner id -> (geometry, area_km2); point_area_added maps tag_point_id -> how
            much its own cluster's hull grew (in km2) when that point was added (only
            meaningful/computed for the band grouping, on the first call).
        """
        owner_points: Dict[int, List[TagPoint]] = {}
        for point in points:
            owner_points.setdefault(group_key(point), []).append(point)

        owner_geometries: Dict[int, BaseGeometry] = {}
        point_area_added: Dict[int, float] = {}

        for owner_id, this_owner_points in owner_points.items():
            cluster_hulls: List[BaseGeometry] = []
            previous_hull_area_m2 = 0.0
            for cluster_points in self._cluster_points(this_owner_points, projected):
                cluster_points_sorted = sorted(cluster_points, key=lambda p: (p.created_at, p.id))
                accumulated: List[Point] = []
                for point in cluster_points_sorted:
                    accumulated.append(projected[point.id])
                    hull = self._hull_of(accumulated)
                    grown_m2 = hull.area - previous_hull_area_m2
                    point_area_added[point.id] = round(max(grown_m2, 0.0) / 1_000_000, 4)
                    previous_hull_area_m2 = hull.area
                cluster_hulls.append(self._hull_of(accumulated))
                previous_hull_area_m2 = 0.0

            combined = unary_union(cluster_hulls)
            if combined.is_empty:
                continue
            owner_geometries[owner_id] = (combined, combined.area / 1_000_000)

        return owner_geometries, point_area_added

    def _cluster_points(self, owner_points: List[TagPoint], projected: Dict[int, Point]) -> List[List[TagPoint]]:
        """
        Group one owner's tags into spatial clusters using single-linkage
        distance clustering (union-find over pairs within `cluster_link_distance`).

        param owner_points: All of one owner's (a band's, or a user's) approved tag points.
        param projected: Each tag point's location, projected to meters, keyed by tag point id.

        :return: A list of clusters, each a list of tag points.
        """
        parent = {point.id: point.id for point in owner_points}

        def find(node_id: int) -> int:
            while parent[node_id] != node_id:
                parent[node_id] = parent[parent[node_id]]
                node_id = parent[node_id]
            return node_id

        def union(a_id: int, b_id: int) -> None:
            root_a, root_b = find(a_id), find(b_id)
            if root_a != root_b:
                parent[root_a] = root_b

        for i, point_a in enumerate(owner_points):
            for point_b in owner_points[i + 1 :]:
                if projected[point_a.id].distance(projected[point_b.id]) <= self.cluster_link_distance:
                    union(point_a.id, point_b.id)

        clusters: Dict[int, List[TagPoint]] = {}
        for point in owner_points:
            clusters.setdefault(find(point.id), []).append(point)

        return list(clusters.values())

    def _hull_of(self, projected_points: List[Point]) -> BaseGeometry:
        if not projected_points:
            return Polygon()
        circles = [pt.buffer(self.radius_meters) for pt in projected_points]
        return unary_union(circles).convex_hull
