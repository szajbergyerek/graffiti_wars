from datetime import datetime

from library.extensions import db


class BandJoinRequest(db.Model):
    """A civilian's pending request to join a band that requires approval to join."""

    __tablename__ = "band_join_requests"
    __table_args__ = (db.UniqueConstraint("band_id", "user_id", name="uq_band_join_request_band_user"),)

    id = db.Column(db.Integer, primary_key=True)
    band_id = db.Column(db.Integer, db.ForeignKey("bands.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    band = db.relationship("Band")
    user = db.relationship("User")
