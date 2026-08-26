from datetime import datetime

from library.extensions import db


class ChatMessage(db.Model):
    """A single text message posted into a conversation."""

    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.String(2000), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    conversation = db.relationship("Conversation", back_populates="messages")
    sender = db.relationship("User")
