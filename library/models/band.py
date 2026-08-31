from datetime import datetime

from library.extensions import db

BAND_COLOR_PALETTE = [
    "#ff2e6c", "#00e0d1", "#ffcc00", "#8c52ff", "#ff7a2e",
    "#3ddc84", "#4d9dff", "#ff4de1", "#a3ff4d", "#ff4d4d",
]

JOIN_POLICIES = ["open", "request", "invite"]


class Band(db.Model):
    """
    A gang that registers a reference tag and claims territory with it.

    `join_policy` controls how civilians can become members: "open" (join
    instantly), "request" (a leader must approve a join request), or
    "invite" (a leader must add the member directly - no self-service join).
    """

    __tablename__ = "bands"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    reference_image_id = db.Column(db.Integer, db.ForeignKey("images.id"), nullable=True)
    banner_image_id = db.Column(db.Integer, db.ForeignKey("images.id"), nullable=True)
    color = db.Column(db.String(7), nullable=False)
    join_policy = db.Column(db.String(10), nullable=False, default="open")
    nationality_code = db.Column(db.String(2), nullable=True)
    founder_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # Disbanding never erases a band - it just gets hidden from every listing.
    # The row, its tags, chat history, and everything else tied to it stays
    # in the database for later use.
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

    members = db.relationship("User", back_populates="band", foreign_keys="User.band_id")
    tag_points = db.relationship("TagPoint", back_populates="band", foreign_keys="TagPoint.band_id")
    territory = db.relationship("BandTerritory", back_populates="band", uselist=False)
    reference_image = db.relationship("Image", foreign_keys=[reference_image_id])
    banner_image = db.relationship("Image", foreign_keys=[banner_image_id])

    @staticmethod
    def next_color(existing_band_count: int) -> str:
        """
        Pick the next color from the rotating palette for a newly created band.

        param existing_band_count: How many bands already exist.

        :return: A hex color string.
        """
        return BAND_COLOR_PALETTE[existing_band_count % len(BAND_COLOR_PALETTE)]
