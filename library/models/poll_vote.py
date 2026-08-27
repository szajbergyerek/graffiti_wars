from library.extensions import db


class PollVote(db.Model):
    """One user's vote for one option in a poll. A user may vote in a poll only once."""

    __tablename__ = "poll_votes"
    __table_args__ = (db.UniqueConstraint("poll_id", "user_id", name="uq_poll_vote_user"),)

    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey("polls.id"), nullable=False)
    option_id = db.Column(db.Integer, db.ForeignKey("poll_options.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    poll = db.relationship("Poll")
    option = db.relationship("PollOption", back_populates="votes")
    user = db.relationship("User")
