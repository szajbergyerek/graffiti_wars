from datetime import datetime

from library.extensions import db


class TagLike(db.Model):
    """One user's like on one tag point. A user may like a tag only once."""

    __tablename__ = "tag_likes"
    __table_args__ = (db.UniqueConstraint("tag_point_id", "user_id", name="uq_tag_like_user"),)

    id = db.Column(db.Integer, primary_key=True)
    tag_point_id = db.Column(db.Integer, db.ForeignKey("tag_points.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    tag_point = db.relationship("TagPoint")
    user = db.relationship("User")
