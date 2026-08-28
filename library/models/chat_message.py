from datetime import datetime

from library.extensions import db


class ChatMessage(db.Model):
    """
    A single message posted into a conversation.

    `message_type` distinguishes what the message carries: "text" (the
    `body`), "image" (`image_id`), "location" (`lat`/`lon`), "poll" (a
    linked `Poll` row), or "tag_added" (a system announcement, linking to
    `tag_point_id`, posted automatically when a band member submits a tag).
    """

    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.String(2000), nullable=False, default="")
    message_type = db.Column(db.String(16), nullable=False, default="text")
    image_id = db.Column(db.Integer, db.ForeignKey("images.id"), nullable=True)
    lat = db.Column(db.Float, nullable=True)
    lon = db.Column(db.Float, nullable=True)
    tag_point_id = db.Column(db.Integer, db.ForeignKey("tag_points.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    conversation = db.relationship("Conversation", back_populates="messages")
    sender = db.relationship("User")
    image = db.relationship("Image", foreign_keys=[image_id])
    poll = db.relationship("Poll", back_populates="chat_message", uselist=False)
    tag_point = db.relationship("TagPoint")
