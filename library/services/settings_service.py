from typing import Dict

from library.extensions import db
from library.models.site_setting import SiteSetting

# Every admin-editable numeric threshold in the app, with its built-in
# default. A key with no matching `SiteSetting` row uses this default.
# Labels/descriptions shown in the admin UI live in translations.py as
# "setting.<key>_label" / "setting.<key>_description", not here - all
# user-facing text belongs in the central translation table.
DEFAULT_SETTINGS: Dict[str, float] = {
    "tag_radius_meters": 100.0,
    "cluster_link_multiplier": 4.0,
    "log_visit_max_distance_meters": 10.0,
    "max_travel_speed_kmh": 140.0,
    "teleport_distance_tolerance_meters": 15.0,
    "local_leaderboard_radius_km": 25.0,
    "overpass_timeout_seconds": 25.0,
    "username_min_length": 3.0,
    "username_max_length": 24.0,
    "poll_min_options": 2.0,
    "poll_max_options": 10.0,
    "max_upload_size_mb": 10.0,
    "image_max_dimension_px": 1920.0,
    "image_jpeg_quality": 82.0,
    "duplicate_tag_radius_meters": 15.0,
    "duplicate_tag_window_minutes": 60.0,
    "tag_submit_rate_limit_count": 10.0,
    "tag_submit_rate_limit_window_minutes": 60.0,
    "tag_visit_rate_limit_count": 20.0,
    "tag_visit_rate_limit_window_minutes": 60.0,
    "tag_comment_rate_limit_count": 20.0,
    "tag_comment_rate_limit_window_minutes": 10.0,
}


class SettingsService:
    """Reads and writes admin-editable numeric configuration values, backed by the `site_settings` table."""

    def get(self, key: str) -> float:
        """
        Get the current effective value of a setting.

        param key: One of the keys in DEFAULT_SETTINGS.

        :return: The admin-stored value if one exists, otherwise the built-in default.
        """
        setting = db.session.get(SiteSetting, key)
        return setting.value if setting is not None else DEFAULT_SETTINGS[key]

    def get_int(self, key: str) -> int:
        """
        Get the current effective value of a setting, rounded to the nearest int.

        param key: One of the keys in DEFAULT_SETTINGS.

        :return: The effective value as an int.
        """
        return round(self.get(key))

    def get_all(self) -> Dict[str, float]:
        """
        Get the current effective value of every known setting.

        :return: A dict of key -> current value (admin override or default), one entry per DEFAULT_SETTINGS key.
        """
        overrides = {row.key: row.value for row in SiteSetting.query.all()}
        return {key: overrides.get(key, default) for key, default in DEFAULT_SETTINGS.items()}

    def set(self, key: str, value: float) -> None:
        """
        Store an admin override for a setting. Does not commit.

        param key: One of the keys in DEFAULT_SETTINGS.
        param value: The new value to store.

        :return: None.
        """
        setting = db.session.get(SiteSetting, key)
        if setting is None:
            db.session.add(SiteSetting(key=key, value=value))
        else:
            setting.value = value
