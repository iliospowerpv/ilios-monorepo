import enum

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, ForeignKey, Identity, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression

from app.db.base_class import Base
from app.models.helpers import utcnow


class FileParsingStatuses(enum.Enum):
    not_started = "Not Started"
    processing_timeout = "Processing Timeout"
    processing_start_failed = "Processing Start Failed"
    processing = "Processing"
    processing_failed = "Processing Failed"
    unprocessable_file = "Unprocessable File"
    completed = "Completed"


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    filepath = Column(String)
    filename = Column(String)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))

    deleted = Column(Boolean, nullable=False, default=False, server_default=expression.false())
    is_actual = Column(Boolean, nullable=False, default=False, server_default=expression.false())

    user = relationship("User", back_populates="files")
    document = relationship("Document", back_populates="files")
    ai_parsing_results = relationship("AIParsingResult", back_populates="file", order_by="AIParsingResult.id.desc()")

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())

    @property
    def latest_ai_result(self):
        return self.ai_parsing_results[0] if self.ai_parsing_results else None


class AIParsingResult(Base):
    __tablename__ = "ai_parsing_results"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"))

    status = Column(Enum(FileParsingStatuses), nullable=True)
    result = Column(JSON, nullable=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)

    ai_model_version = Column(String, nullable=True)
    ai_app_version = Column(String, nullable=True)

    file = relationship("File", back_populates="ai_parsing_results")  # noqa: VNE002

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())
