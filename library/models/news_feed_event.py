from datetime import datetime

from library.extensions import db


class NewsFeedEvent(db.Model):
    """A short, timestamped entry shown on the public activity feed."""

    __tablename__ = "news_feed_events"

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(32), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    band_id = db.Column(db.Integer, db.ForeignKey("bands.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    band = db.relationship("Band")
