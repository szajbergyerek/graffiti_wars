import json
from typing import Dict, List

from shapely.geometry import Point, mapping
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from library.extensions import db
from library.models.band_territory import BandTerritory
from library.models.tag_point import TagPoint
from library.services.geo_projector import GeoProjector


class TerritoryEngine:
    """
    Recomputes every band's territory from scratch.

    A band's tags are first grouped into spatial clusters: two tags belong
    to the same cluster if they are within `cluster_link_distance` of each
    other (chained transitively, so a "necklace" of nearby tags all merge
    into one group even if the two ends are farther apart than the
    threshold). Each cluster's claim is the convex hull of its own
    (buffered) tags, so the "attraction zone" between tags in the same
    neighborhood is filled in - but a tag on the other side of the map
    starts its own separate cluster instead of dragging a claimed corridor
    across everything in between.

    Clusters are then replayed in chronological order using a painter's
    algorithm: whenever a cluster's up-to-date hull overlaps another
    cluster's claim - whatever band that belongs to - the newer hull always
    wins in the overlap. A band's final territory is the union of all of
    its own clusters. This still produces a point dropped deep inside enemy
    territory carving a hole out of it, and a band reclaiming lost ground
    by tagging again inside the old radius, since that new tag is always
    the most recent event there - just scoped to whichever cluster it
    actually lands in.
    """

    def __init__(self, radius_meters: float = 100.0, cluster_link_multiplier: float = 4.0) -> None:
        self.radius_meters = radius_meters
        self.cluster_link_distance = radius_meters * cluster_link_multiplier

    def recompute_all(self) -> None:
        """
        Replay every approved tag point in creation order and persist the
        resulting per-band territory polygons, replacing whatever was stored before.

        :return: None
        """
        points = (
            TagPoint.query.filter_by(status="approved")
            .order_by(TagPoint.created_at.asc(), TagPoint.id.asc())
            .all()
        )

        BandTerritory.query.delete()

        if not points:
            db.session.commit()
            return

        center_lat = sum(p.lat for p in points) / len(points)
        center_lon = sum(p.lon for p in points) / len(points)
        projector = GeoProjector(center_lat, center_lon)

        projected = {point.id: projector.to_meters(Point(point.lon, point.lat)) for point in points}

        band_points: Dict[int, List[TagPoint]] = {}
        for point in points:
            band_points.setdefault(point.band_id, []).append(point)

        cluster_of: Dict[int, int] = {}
        cluster_band: Dict[int, int] = {}
        next_cluster_id = 0
        for band_id, this_band_points in band_points.items():
            for cluster_points in self._cluster_points(this_band_points, projected):
                for point in cluster_points:
                    cluster_of[point.id] = next_cluster_id
                cluster_band[next_cluster_id] = band_id
                next_cluster_id += 1

        cluster_points_so_far: Dict[int, List[Point]] = {}
        cluster_geometries: Dict[int, BaseGeometry] = {}

        for point in points:
            cluster_id = cluster_of[point.id]
            cluster_points_so_far.setdefault(cluster_id, []).append(projected[point.id])
            hull = self._hull_of(cluster_points_so_far[cluster_id])

            for other_cluster_id in list(cluster_geometries.keys()):
                if cluster_band[other_cluster_id] == point.band_id:
                    continue
                existing = cluster_geometries[other_cluster_id]
                if existing.intersects(hull):
                    cluster_geometries[other_cluster_id] = existing.difference(hull)

            cluster_geometries[cluster_id] = hull

        band_geometries: Dict[int, List[BaseGeometry]] = {}
        for cluster_id, geometry in cluster_geometries.items():
            if geometry.is_empty:
                continue
            band_geometries.setdefault(cluster_band[cluster_id], []).append(geometry)

        for band_id, geometries in band_geometries.items():
            combined = unary_union(geometries)
            if combined.is_empty:
                continue
            wgs84_geometry = projector.to_wgs84(combined)
            area_km2 = combined.area / 1_000_000
            db.session.add(
                BandTerritory(band_id=band_id, geojson=json.dumps(mapping(wgs84_geometry)), area_km2=area_km2)
            )

        db.session.commit()

    def _cluster_points(self, band_points: List[TagPoint], projected: Dict[int, Point]) -> List[List[TagPoint]]:
        """
        Group one band's tags into spatial clusters using single-linkage
        distance clustering (union-find over pairs within `cluster_link_distance`).

        param band_points: All of one band's approved tag points.
        param projected: Each tag point's location, projected to meters, keyed by tag point id.

        :return: A list of clusters, each a list of tag points.
        """
        parent = {point.id: point.id for point in band_points}

        def find(node_id: int) -> int:
            while parent[node_id] != node_id:
                parent[node_id] = parent[parent[node_id]]
                node_id = parent[node_id]
            return node_id

        def union(a_id: int, b_id: int) -> None:
            root_a, root_b = find(a_id), find(b_id)
            if root_a != root_b:
                parent[root_a] = root_b

        for i, point_a in enumerate(band_points):
            for point_b in band_points[i + 1 :]:
                if projected[point_a.id].distance(projected[point_b.id]) <= self.cluster_link_distance:
                    union(point_a.id, point_b.id)

        clusters: Dict[int, List[TagPoint]] = {}
        for point in band_points:
            clusters.setdefault(find(point.id), []).append(point)

        return list(clusters.values())

    def _hull_of(self, projected_points: List[Point]) -> BaseGeometry:
        circles = [pt.buffer(self.radius_meters) for pt in projected_points]
        return unary_union(circles).convex_hull
