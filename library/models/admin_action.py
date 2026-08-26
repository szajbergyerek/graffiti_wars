from datetime import datetime

from library.extensions import db


class AdminAction(db.Model):
    """Audit log entry for a moderation action taken by an administrator."""

    __tablename__ = "admin_actions"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action_type = db.Column(db.String(32), nullable=False)
    target_description = db.Column(db.String(255), nullable=False)
    reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    admin = db.relationship("User")
