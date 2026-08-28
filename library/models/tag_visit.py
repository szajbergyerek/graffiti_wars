from datetime import datetime

from library.extensions import db


class TagVisit(db.Model):
    """A log entry: a user was physically at someone else's tag and photographed it."""

    __tablename__ = "tag_visits"

    id = db.Column(db.Integer, primary_key=True)
    tag_point_id = db.Column(db.Integer, db.ForeignKey("tag_points.id"), nullable=False)
    visitor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    photo_image_id = db.Column(db.Integer, db.ForeignKey("images.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    tag_point = db.relationship("TagPoint")
    visitor = db.relationship("User")
    photo_image = db.relationship("Image")
