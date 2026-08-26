from datetime import datetime

from library.extensions import db


class Conversation(db.Model):
    """A message thread: either a 1:1 direct chat, or a band's group chat."""

    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(10), nullable=False)
    band_id = db.Column(db.Integer, db.ForeignKey("bands.id"), nullable=True, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    band = db.relationship("Band")
    participants = db.relationship("ConversationParticipant", back_populates="conversation")
    messages = db.relationship(
        "ChatMessage", back_populates="conversation", order_by="ChatMessage.created_at"
    )
