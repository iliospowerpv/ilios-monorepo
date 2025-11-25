from sqlalchemy import VARCHAR, Column, DateTime, ForeignKey, Identity, Integer

from app.db.base_class import Base
from app.models.helpers import utcnow


class ChatBotConversation(Base):
    __tablename__ = "chatbot_conversations"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"))
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))
    conversation_id = Column(VARCHAR, unique=True)

    # setting up the server_default value, that will be filled on the database side
    created_at = Column(DateTime, server_default=utcnow())
    # by the updated_at it is possible to check when the user last time updated token
    updated_at = Column(DateTime, server_default=utcnow())
