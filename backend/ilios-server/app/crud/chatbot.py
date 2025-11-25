from app.crud.base_crud import BaseCRUD
from app.models.chatbot import ChatBotConversation


class ChatBotConversationsCRUD(BaseCRUD):
    """CRUD operations on ChatBotConversation model."""

    def __init__(self, db_session):
        super().__init__(model=ChatBotConversation, db_session=db_session)

    def get_by_conversation_id(self, site_id, conversation_id):
        return (
            self.db_session.query(self.model)
            .filter_by(conversation_id=conversation_id)
            .filter_by(site_id=site_id)
            .one_or_none()
        )
