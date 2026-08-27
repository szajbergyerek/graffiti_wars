from library.extensions import db


class PollOption(db.Model):
    """A single selectable answer for a poll."""

    __tablename__ = "poll_options"

    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey("polls.id"), nullable=False)
    text = db.Column(db.String(100), nullable=False)

    poll = db.relationship("Poll", back_populates="options")
    votes = db.relationship("PollVote", back_populates="option")
