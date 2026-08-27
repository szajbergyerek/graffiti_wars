from datetime import datetime

from library.extensions import db


class TagPoint(db.Model):
    """A single photographed, geolocated tag submitted on behalf of a band."""

    __tablename__ = "tag_points"

    id = db.Column(db.Integer, primary_key=True)
    band_id = db.Column(db.Integer, db.ForeignKey("bands.id"), nullable=False)
    submitted_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    photo_image_id = db.Column(db.Integer, db.ForeignKey("images.id"), nullable=True)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(16), nullable=False, default="pending")
    ai_confidence = db.Column(db.Float, nullable=True)
    area_added_km2 = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    removed_reason = db.Column(db.String(255), nullable=True)

    band = db.relationship("Band", back_populates="tag_points", foreign_keys=[band_id])
    submitted_by = db.relationship("User", back_populates="tag_points", foreign_keys=[submitted_by_id])
    photo_image = db.relationship("Image", foreign_keys=[photo_image_id])
