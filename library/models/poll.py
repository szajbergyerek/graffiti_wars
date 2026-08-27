from datetime import datetime

from library.extensions import db


class Poll(db.Model):
    """A single-question poll attached to one chat message in a band group chat."""

    __tablename__ = "polls"

    id = db.Column(db.Integer, primary_key=True)
    chat_message_id = db.Column(db.Integer, db.ForeignKey("chat_messages.id"), nullable=False, unique=True)
    question = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    chat_message = db.relationship("ChatMessage", back_populates="poll")
    options = db.relationship("PollOption", back_populates="poll", order_by="PollOption.id")
