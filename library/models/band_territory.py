from datetime import datetime

from library.extensions import db


class BandTerritory(db.Model):
    """The most recently computed territory polygon owned by a band."""

    __tablename__ = "band_territories"

    band_id = db.Column(db.Integer, db.ForeignKey("bands.id"), primary_key=True)
    geojson = db.Column(db.Text, nullable=False)
    area_km2 = db.Column(db.Float, nullable=False, default=0.0)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    band = db.relationship("Band", back_populates="territory")
