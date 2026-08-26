import pyproj
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


class GeoProjector:
    """Projects geometry between WGS84 lon/lat and a local metric plane centered on a point."""

    def __init__(self, center_lat: float, center_lon: float) -> None:
        """
        Build forward/inverse transformers for an azimuthal equidistant projection
        centered on the given coordinate, so distances and areas computed in the
        projected plane stay accurate near that center.

        param center_lat: Latitude of the projection center, in degrees.
        param center_lon: Longitude of the projection center, in degrees.

        :return: None
        """
        local_crs = pyproj.CRS.from_proj4(
            f"+proj=aeqd +lat_0={center_lat} +lon_0={center_lon} +units=m +ellps=WGS84"
        )
        self._to_meters = pyproj.Transformer.from_crs("EPSG:4326", local_crs, always_xy=True).transform
        self._to_wgs84 = pyproj.Transformer.from_crs(local_crs, "EPSG:4326", always_xy=True).transform

    def to_meters(self, geometry: BaseGeometry) -> BaseGeometry:
        """
        Project a lon/lat geometry into the local metric plane.

        param geometry: A shapely geometry with (lon, lat) coordinates.

        :return: The equivalent geometry in meters.
        """
        return transform(self._to_meters, geometry)

    def to_wgs84(self, geometry: BaseGeometry) -> BaseGeometry:
        """
        Project a geometry from the local metric plane back to lon/lat.

        param geometry: A shapely geometry in meters.

        :return: The equivalent geometry in (lon, lat) degrees.
        """
        return transform(self._to_wgs84, geometry)
