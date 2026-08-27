from datetime import datetime

from library.extensions import db


class TagComment(db.Model):
    """A single text comment posted on a tag point."""

    __tablename__ = "tag_comments"

    id = db.Column(db.Integer, primary_key=True)
    tag_point_id = db.Column(db.Integer, db.ForeignKey("tag_points.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    tag_point = db.relationship("TagPoint")
    user = db.relationship("User")
