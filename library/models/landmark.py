from datetime import datetime

from library.extensions import db

LANDMARK_CATEGORIES = ["amenity", "shop", "tourism", "leisure", "historic", "office"]


class Landmark(db.Model):
    """A single OpenStreetMap point of interest found inside a band's territory."""

    __tablename__ = "landmarks"
    __table_args__ = (db.UniqueConstraint("band_id", "osm_id", name="uq_landmark_band_osm"),)

    id = db.Column(db.Integer, primary_key=True)
    band_id = db.Column(db.Integer, db.ForeignKey("bands.id"), nullable=False)
    osm_id = db.Column(db.String(30), nullable=False)
    category = db.Column(db.String(20), nullable=False)
    subtype = db.Column(db.String(50), nullable=True)
    name = db.Column(db.String(200), nullable=True)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    band = db.relationship("Band")
