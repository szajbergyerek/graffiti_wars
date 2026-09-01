from datetime import datetime

from library.extensions import db


class Image(db.Model):
    """
    A single uploaded image file, stored on disk under a content hash and
    tracked here so callers reference it by id instead of a raw path.
    Room is left here for metadata (EXIF, AI tags, ...) to be added later
    without touching whatever model links to it.
    """

    __tablename__ = "images"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(20), nullable=False)
    file_hash = db.Column(db.String(64), nullable=False)
    extension = db.Column(db.String(10), nullable=False)
    relative_path = db.Column(db.String(255), nullable=False, unique=True)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Only set for categories that run server-side tag detection ("tags",
    # "tag_visits") - the detector's bounding box, in this image's own pixel
    # coordinates, and its confidence for that box.
    detection_x1 = db.Column(db.Float, nullable=True)
    detection_y1 = db.Column(db.Float, nullable=True)
    detection_x2 = db.Column(db.Float, nullable=True)
    detection_y2 = db.Column(db.Float, nullable=True)
    detection_confidence = db.Column(db.Float, nullable=True)

    uploaded_by = db.relationship("User", foreign_keys=[uploaded_by_id])

    @property
    def url(self) -> str:
        """
        Build the public URL this image is served from.

        :return: The absolute path (from the site root) to fetch this image.
        """
        from flask import url_for

        return url_for("assets.serve_image", relative_path=self.relative_path)
