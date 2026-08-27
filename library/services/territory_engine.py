import json
from typing import Dict, List, Tuple

from shapely.geometry import Point, Polygon, mapping
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

    On top of that, an explicit reclaim rule runs before each point is
    added: if the new tag's own attraction circle (its buffer(radius))
    touches the attraction circle of an enemy tag that is currently
    encroaching on the new tag's cluster, that enemy tag is neutralized -
    it stops contributing to its cluster's hull from that point on (it
    stays on the map as a normal tag, it just no longer holds ground), and
    the defending cluster's territory is restored immediately rather than
    waiting for the enemy cluster to happen to shrink on its own.
    """

    def __init__(self, radius_meters: float = 100.0, cluster_link_multiplier: float = 4.0) -> None:
        self.radius_meters = radius_meters
        self.cluster_link_distance = radius_meters * cluster_link_multiplier

    def recompute_all(self) -> None:
        """
        Replay every approved tag point in creation order and persist the
        resulting per-band territory polygons, replacing whatever was stored
        before. Each point's own contribution to its cluster's hull growth is
        computed in the same pass and cached on the point, so tag detail pages
        can read it directly instead of re-running this whole replay live.

        :return: None
        """
        points = (
            TagPoint.query.filter_by(status="approved")
            .order_by(TagPoint.created_at.asc(), TagPoint.id.asc())
            .all()
        )

        BandTerritory.query.delete()

        band_areas, point_area_added = self._compute_band_geometries(points)
        for band_id, (geojson_str, area_km2) in band_areas.items():
            db.session.add(BandTerritory(band_id=band_id, geojson=geojson_str, area_km2=area_km2))

        for point in points:
            point.area_added_km2 = point_area_added.get(point.id, 0.0)

        db.session.commit()

    def _compute_band_geometries(self, points: List[TagPoint]) -> tuple:
        """
        Run the clustering + painter's-algorithm replay over an arbitrary set of
        approved tag points, without touching the database.

        param points: Approved tag points, in chronological order.

        :return: A (band_geometries, point_area_added) tuple - band_geometries maps
            band_id -> (geojson string, area_km2) for bands that ended up with
            territory; point_area_added maps tag_point_id -> how much its own
            cluster's hull grew (in km2) when that point was added.
        """
        if not points:
            return {}, {}

        center_lat = sum(p.lat for p in points) / len(points)
        center_lon = sum(p.lon for p in points) / len(points)
        projector = GeoProjector(center_lat, center_lon)

        projected = {point.id: projector.to_meters(Point(point.lon, point.lat)) for point in points}
        circles = {point_id: geom.buffer(self.radius_meters) for point_id, geom in projected.items()}
        band_of: Dict[int, int] = {point.id: point.band_id for point in points}

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

        # Spatial grid over the (fixed) point positions, so the reclaim check
        # doesn't have to compare every new point against every earlier one.
        # A cell size equal to the max touch distance between two circles
        # (2 * radius) guarantees any touching neighbor lies in the 3x3 block
        # of cells around the query point's own cell.
        cell_size = max(self.radius_meters * 2, 1.0)
        grid: Dict[Tuple[int, int], List[int]] = {}

        def cell_of(pt: Point) -> Tuple[int, int]:
            return (int(pt.x // cell_size), int(pt.y // cell_size))

        def nearby_point_ids(pt: Point) -> List[int]:
            cx, cy = cell_of(pt)
            result: List[int] = []
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    result.extend(grid.get((cx + dx, cy + dy), []))
            return result

        active_ids: Dict[int, List[int]] = {}  # cluster_id -> active point ids, in insertion order
        cluster_points_so_far: Dict[int, List[Point]] = {}
        cluster_geometries: Dict[int, BaseGeometry] = {}
        neutralized: set = set()

        point_area_added: Dict[int, float] = {}
        previous_hull_area_m2: Dict[int, float] = {}

        def rebuild_cluster(cluster_id: int) -> BaseGeometry:
            hull = self._hull_of(cluster_points_so_far.get(cluster_id, []))
            cluster_geometries[cluster_id] = hull
            return hull

        for point in points:
            cluster_id = cluster_of[point.id]
            point_circle = circles[point.id]

            # --- Reclaim check: does this new tag's circle free up ground
            # that an enemy tag is currently holding against this cluster? ---
            defended_hull = self._hull_of(cluster_points_so_far.get(cluster_id, []))
            if not defended_hull.is_empty:
                for candidate_id in nearby_point_ids(projected[point.id]):
                    if candidate_id in neutralized or band_of[candidate_id] == point.band_id:
                        continue
                    candidate_cluster = cluster_of[candidate_id]
                    if candidate_id not in active_ids.get(candidate_cluster, []):
                        continue
                    if not point_circle.intersects(circles[candidate_id]):
                        continue
                    if not circles[candidate_id].intersects(defended_hull):
                        continue

                    # candidate_id is an enemy tag encroaching on this cluster
                    # and touching the new tag - neutralize it and give the
                    # ground back immediately.
                    neutralized.add(candidate_id)
                    active_ids[candidate_cluster] = [
                        pid for pid in active_ids[candidate_cluster] if pid != candidate_id
                    ]
                    cluster_points_so_far[candidate_cluster] = [
                        projected[pid] for pid in active_ids[candidate_cluster]
                    ]
                    rebuild_cluster(candidate_cluster)

            # --- Normal chronological growth + carve, using active points only ---
            active_ids.setdefault(cluster_id, []).append(point.id)
            cluster_points_so_far.setdefault(cluster_id, []).append(projected[point.id])
            hull = self._hull_of(cluster_points_so_far[cluster_id])

            grown_m2 = hull.area - previous_hull_area_m2.get(cluster_id, 0.0)
            point_area_added[point.id] = round(max(grown_m2, 0.0) / 1_000_000, 4)
            previous_hull_area_m2[cluster_id] = hull.area

            for other_cluster_id in list(cluster_geometries.keys()):
                if cluster_band[other_cluster_id] == point.band_id:
                    continue
                existing = cluster_geometries[other_cluster_id]
                if existing.intersects(hull):
                    cluster_geometries[other_cluster_id] = existing.difference(hull)

            cluster_geometries[cluster_id] = hull

            grid.setdefault(cell_of(projected[point.id]), []).append(point.id)

        band_geometries: Dict[int, List[BaseGeometry]] = {}
        for cluster_id, geometry in cluster_geometries.items():
            if geometry.is_empty:
                continue
            band_geometries.setdefault(cluster_band[cluster_id], []).append(geometry)

        result: Dict[int, tuple] = {}
        for band_id, geometries in band_geometries.items():
            combined = unary_union(geometries)
            if combined.is_empty:
                continue
            wgs84_geometry = projector.to_wgs84(combined)
            area_km2 = combined.area / 1_000_000
            result[band_id] = (json.dumps(mapping(wgs84_geometry)), area_km2)

        return result, point_area_added

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
        if not projected_points:
            return Polygon()
        circles = [pt.buffer(self.radius_meters) for pt in projected_points]
        return unary_union(circles).convex_hull
