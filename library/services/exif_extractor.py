import logging
from datetime import datetime
from typing import Optional

from PIL import Image as PILImage
from PIL.ExifTags import GPSTAGS, TAGS

logger = logging.getLogger("exif_extractor")

GPS_IFD_TAG = 0x8825


class ExifExtractor:
    """
    Reads capture time, last-modified time, and GPS coordinates out of a
    photo's EXIF metadata, and logs everything it finds so real-world
    metadata can be inspected while the freshness/authenticity checks are
    still being tuned.
    """

    def extract(self, file_path: str) -> dict:
        """
        Read whatever EXIF metadata is available from an image file.

        param file_path: Path to the image file on disk.

        :return: A dict with "date_taken", "date_modified" (datetime or None), and "gps_lat"/"gps_lon" (float or None).
        """
        result = {"date_taken": None, "date_modified": None, "gps_lat": None, "gps_lon": None}

        with PILImage.open(file_path) as image:
            exif_data = image.getexif()

            if not exif_data:
                logger.info("No EXIF data found in %s", file_path)
                return result

            tags = {TAGS.get(tag_id, tag_id): value for tag_id, value in exif_data.items()}

            date_taken_raw = tags.get("DateTimeOriginal") or tags.get("DateTimeDigitized")
            result["date_taken"] = self._parse_exif_datetime(date_taken_raw)

            date_modified_raw = tags.get("DateTime")
            result["date_modified"] = self._parse_exif_datetime(date_modified_raw)

            gps_ifd = exif_data.get_ifd(GPS_IFD_TAG)
            if gps_ifd:
                gps_tags = {GPSTAGS.get(tag_id, tag_id): value for tag_id, value in gps_ifd.items()}
                result["gps_lat"] = self._convert_gps(gps_tags.get("GPSLatitude"), gps_tags.get("GPSLatitudeRef"))
                result["gps_lon"] = self._convert_gps(gps_tags.get("GPSLongitude"), gps_tags.get("GPSLongitudeRef"))

        logger.info("Extracted EXIF metadata from %s: %s", file_path, result)
        return result

    def _parse_exif_datetime(self, raw: Optional[str]) -> Optional[datetime]:
        if not raw:
            return None
        try:
            return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S")
        except ValueError:
            return None

    def _convert_gps(self, value, ref) -> Optional[float]:
        if value is None or ref is None:
            return None
        degrees, minutes, seconds = value
        decimal = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
        if ref in ("S", "W"):
            decimal = -decimal
        return decimal
