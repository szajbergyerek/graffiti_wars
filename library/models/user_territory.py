from datetime import datetime

from library.extensions import db


class UserTerritory(db.Model):
    """The most recently computed personal territory polygon covered by a single user's own tags."""

    __tablename__ = "user_territories"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    geojson = db.Column(db.Text, nullable=False)
    area_km2 = db.Column(db.Float, nullable=False, default=0.0)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", back_populates="territory")
