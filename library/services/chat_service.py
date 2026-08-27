from typing import Optional

from library.extensions import db
from library.models.band import Band
from library.models.chat_message import ChatMessage
from library.models.conversation import Conversation
from library.models.conversation_participant import ConversationParticipant
from library.models.user import User


class ChatService:
    """Finds or creates conversations and posts messages into them."""

    def find_direct_conversation(self, user_a: User, user_b: User) -> Optional[Conversation]:
        """
        Find the existing 1:1 conversation between two users, if any.

        param user_a: One participant.
        param user_b: The other participant.

        :return: The direct conversation between them, or None if they have never talked.
        """
        shared = (
            Conversation.query.join(ConversationParticipant)
            .filter(Conversation.kind == "direct", ConversationParticipant.user_id.in_([user_a.id, user_b.id]))
            .all()
        )
        counts: dict = {}
        for conversation in shared:
            counts[conversation.id] = counts.get(conversation.id, 0) + 1
        for conversation_id, count in counts.items():
            if count == 2:
                return db.session.get(Conversation, conversation_id)
        return None

    def get_or_create_direct_conversation(self, user_a: User, user_b: User) -> Conversation:
        """
        Find the existing 1:1 conversation between two users, or start a new one.

        param user_a: One participant.
        param user_b: The other participant.

        :return: The direct conversation between them.
        """
        existing = self.find_direct_conversation(user_a, user_b)
        if existing is not None:
            return existing

        conversation = Conversation(kind="direct")
        db.session.add(conversation)
        db.session.flush()
        db.session.add(ConversationParticipant(conversation_id=conversation.id, user_id=user_a.id))
        db.session.add(ConversationParticipant(conversation_id=conversation.id, user_id=user_b.id))
        db.session.commit()
        return conversation

    def create_band_conversation(self, band: Band) -> Conversation:
        """
        Create the group chat for a newly created band, with its founder as the first participant.

        param band: The band to create a chat for.

        :return: The new band conversation.
        """
        conversation = Conversation(kind="band", band_id=band.id)
        db.session.add(conversation)
        db.session.flush()
        db.session.add(ConversationParticipant(conversation_id=conversation.id, user_id=band.founder_id))
        return conversation

    def add_band_member(self, band: Band, user: User) -> None:
        """
        Add a user to their band's group chat.

        param band: The band the user just joined.
        param user: The user to add as a chat participant.

        :return: None
        """
        conversation = Conversation.query.filter_by(kind="band", band_id=band.id).first()
        if conversation is None:
            return
        already_in = ConversationParticipant.query.filter_by(
            conversation_id=conversation.id, user_id=user.id
        ).first()
        if already_in is None:
            db.session.add(ConversationParticipant(conversation_id=conversation.id, user_id=user.id))

    def remove_band_member(self, band: Band, user: User) -> None:
        """
        Remove a user from their former band's group chat.

        param band: The band the user just left.
        param user: The user to remove from the chat.

        :return: None
        """
        conversation = Conversation.query.filter_by(kind="band", band_id=band.id).first()
        if conversation is None:
            return
        ConversationParticipant.query.filter_by(conversation_id=conversation.id, user_id=user.id).delete()

    def is_participant(self, conversation: Conversation, user: User) -> bool:
        """
        Check whether a user is allowed to read/post in a conversation.

        param conversation: The conversation to check.
        param user: The user to check.

        :return: True if the user is a participant.
        """
        return (
            ConversationParticipant.query.filter_by(conversation_id=conversation.id, user_id=user.id).first()
            is not None
        )

    def post_message(self, conversation: Conversation, sender: User, body: str) -> ChatMessage:
        """
        Append a new message to a conversation.

        param conversation: The conversation to post into.
        param sender: The user sending the message.
        param body: The message text.

        :return: The newly created message.
        """
        message = ChatMessage(conversation_id=conversation.id, sender_id=sender.id, body=body)
        db.session.add(message)
        db.session.commit()
        self.mark_read(conversation, sender)
        return message

    def mark_read(self, conversation: Conversation, user: User) -> None:
        """
        Mark every message currently in a conversation as read by a user.

        param conversation: The conversation being viewed.
        param user: The user who just viewed it.

        :return: None
        """
        latest = ChatMessage.query.filter_by(conversation_id=conversation.id).order_by(ChatMessage.id.desc()).first()
        if latest is None:
            return
        participant = ConversationParticipant.query.filter_by(
            conversation_id=conversation.id, user_id=user.id
        ).first()
        if participant is None:
            return
        if participant.last_read_message_id is None or latest.id > participant.last_read_message_id:
            participant.last_read_message_id = latest.id
            db.session.commit()

    def unread_count(self, user: User) -> int:
        """
        Count how many messages sent by other people are unread across all of a user's conversations.

        param user: The user to count unread messages for.

        :return: The total unread message count.
        """
        total = 0
        participants = ConversationParticipant.query.filter_by(user_id=user.id).all()
        for participant in participants:
            query = ChatMessage.query.filter(
                ChatMessage.conversation_id == participant.conversation_id,
                ChatMessage.sender_id != user.id,
            )
            if participant.last_read_message_id is not None:
                query = query.filter(ChatMessage.id > participant.last_read_message_id)
            total += query.count()
        return total
