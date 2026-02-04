import enum

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, ForeignKey, Identity, Integer, String, Text
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
    storage_key = Column(String(500), nullable=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))

    deleted = Column(Boolean, nullable=False, default=False, server_default=expression.false())
    is_actual = Column(Boolean, nullable=False, default=False, server_default=expression.false())

    version_number = Column(Integer, nullable=True)
    version_label = Column(String(100), nullable=True)
    change_notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="files")
    document = relationship("Document", back_populates="files")
    ai_parsing_results = relationship("AIParsingResult", back_populates="file", order_by="AIParsingResult.id.desc()")
    document_keys = relationship("DocumentKey", back_populates="file")
    project_facts = relationship("ProjectFact", back_populates="source_file")
    assumption_promotions = relationship("AssumptionPromotion", back_populates="file")

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())

    @property
    def latest_ai_result(self):
        return self.ai_parsing_results[0] if self.ai_parsing_results else None

    @property
    def is_current_version(self):
        return self.is_actual and not self.deleted

    @property
    def version_display(self):
        if self.version_label:
            return self.version_label
        if self.version_number:
            return f"v{self.version_number}"
        return f"Version {self.id}"


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

    document_type_id = Column(Integer, ForeignKey("extraction_document_types.id", ondelete="SET NULL"), nullable=True)
    schema_version_id = Column(Integer, ForeignKey("extraction_schema_versions.id", ondelete="SET NULL"), nullable=True)
    prompt_template_id = Column(Integer, ForeignKey("extraction_prompt_templates.id", ondelete="SET NULL"), nullable=True)
    raw_llm_response = Column(Text, nullable=True)
    parsed_result = Column(JSON, nullable=True)
    extraction_run_number = Column(Integer, nullable=True, default=1)
    retries = Column(Integer, nullable=True, default=0)
    error_message = Column(Text, nullable=True)
    is_reprocess = Column(Boolean, nullable=True, default=False)
    force_reprocess = Column(Boolean, nullable=True, default=False)

    file = relationship("File", back_populates="ai_parsing_results")  # noqa: VNE002
    document_type = relationship("ExtractionDocumentType")
    schema_version = relationship("ExtractionSchemaVersion")
    prompt_template = relationship("ExtractionPromptTemplate")

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())
