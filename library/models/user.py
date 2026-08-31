from datetime import datetime
from urllib.parse import quote

from flask_login import UserMixin

from library.extensions import db


class User(db.Model, UserMixin):
    """A registered player, authenticated via Google. Belongs to at most one band; no band means civilian."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    avatar_seed = db.Column(db.String(64), nullable=False)
    avatar_url = db.Column(db.String(500), nullable=True)
    avatar_image_id = db.Column(db.Integer, db.ForeignKey("images.id"), nullable=True)
    banner_image_id = db.Column(db.Integer, db.ForeignKey("images.id"), nullable=True)
    bio = db.Column(db.String(300), nullable=True)
    nationality_code = db.Column(db.String(2), nullable=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    is_banned = db.Column(db.Boolean, nullable=False, default=False)
    allow_direct_messages = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Last location a tag submission or tag-visit log was accepted from, used
    # only for teleport-speed anti-cheat checks (see endpoints/tags.py) - not
    # shown anywhere in the UI.
    last_location_lat = db.Column(db.Float, nullable=True)
    last_location_lon = db.Column(db.Float, nullable=True)
    last_location_at = db.Column(db.DateTime, nullable=True)

    band_id = db.Column(db.Integer, db.ForeignKey("bands.id"), nullable=True)
    band_role = db.Column(db.String(16), nullable=True)
    band_joined_at = db.Column(db.DateTime, nullable=True)

    band = db.relationship("Band", back_populates="members", foreign_keys=[band_id])
    tag_points = db.relationship(
        "TagPoint", back_populates="submitted_by", foreign_keys="TagPoint.submitted_by_id"
    )
    territory = db.relationship("UserTerritory", back_populates="user", uselist=False)
    avatar_image = db.relationship("Image", foreign_keys=[avatar_image_id])
    banner_image = db.relationship("Image", foreign_keys=[banner_image_id])

    @property
    def is_civilian(self) -> bool:
        """
        Determine whether this user currently belongs to no band.

        :return: True if the user has not joined any band.
        """
        return self.band_id is None

    @property
    def display_avatar_url(self) -> str:
        """
        Pick the best available avatar: a self-uploaded image first, then the
        Google account picture, then a generated placeholder.

        :return: A URL usable directly as an <img> src.
        """
        if self.avatar_image is not None:
            return self.avatar_image.url
        if self.avatar_url:
            return self.avatar_url
        return f"https://api.dicebear.com/7.x/shapes/svg?seed={quote(self.avatar_seed)}"
