from library.extensions import db


class SiteSetting(db.Model):
    """
    A single admin-editable numeric configuration value, keyed by name.

    Only rows with an admin-set override live here - a key with no row falls
    back to its built-in default in `SettingsService.DEFAULT_SETTINGS`.
    """

    __tablename__ = "site_settings"

    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Float, nullable=False)
