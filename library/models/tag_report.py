from datetime import datetime

from library.extensions import db


class TagReport(db.Model):
    """A user-filed report that a previously approved tag is no longer there."""

    __tablename__ = "tag_reports"

    id = db.Column(db.Integer, primary_key=True)
    tag_point_id = db.Column(db.Integer, db.ForeignKey("tag_points.id"), nullable=False)
    reported_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, nullable=False, default=False)
    resolved_at = db.Column(db.DateTime, nullable=True)

    tag_point = db.relationship("TagPoint")
    reported_by = db.relationship("User")
