from library.extensions import db


class ConversationParticipant(db.Model):
    """Membership of one user in one conversation."""

    __tablename__ = "conversation_participants"
    __table_args__ = (
        db.UniqueConstraint("conversation_id", "user_id", name="uq_conversation_participant"),
    )

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    last_read_message_id = db.Column(db.Integer, nullable=True)

    conversation = db.relationship("Conversation", back_populates="participants")
    user = db.relationship("User")
