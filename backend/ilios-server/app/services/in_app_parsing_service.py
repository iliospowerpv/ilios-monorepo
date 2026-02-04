"""In-App AI Parsing Service

Replaces external cloud function for AI document parsing.
Uses Replit AI Integrations (OpenAI) for text extraction and field parsing.

Flow:
1. Download file bytes from Replit Object Storage
2. Extract text from PDF/DOCX using pypdf/python-docx
3. Build prompt using ExtractionPipelineService registry
4. Call OpenAI API for extraction
5. Parse and store results in AIParsingResult

Uses gpt-5.2 model via Replit AI Integrations (no API key required, billed to credits).
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional

from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from app.crud.ai_parsing_result import AIParsingResultCRUD
from app.helpers.files.storage_service import get_storage_service
from app.models.file import File as FileModel, FileParsingStatuses
from app.services.extraction_pipeline_service import ExtractionPipelineService

logger = logging.getLogger(__name__)


def is_rate_limit_error(exception: BaseException) -> bool:
    """Check if the exception is a rate limit or quota violation error."""
    error_msg = str(exception)
    return (
        "429" in error_msg
        or "RATELIMIT_EXCEEDED" in error_msg
        or "quota" in error_msg.lower()
        or "rate limit" in error_msg.lower()
        or (hasattr(exception, "status_code") and exception.status_code == 429)
    )


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes using pypdf."""
    try:
        from pypdf import PdfReader
        pdf_reader = PdfReader(BytesIO(file_bytes))
        text_parts = []
        for page_num, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
        return "\n\n".join(text_parts)
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {e}")
        raise ValueError(f"PDF text extraction failed: {e}")


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX bytes using python-docx."""
    try:
        from docx import Document
        doc = Document(BytesIO(file_bytes))
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells)
                if row_text.strip():
                    text_parts.append(row_text)
        return "\n\n".join(text_parts)
    except Exception as e:
        logger.error(f"Failed to extract text from DOCX: {e}")
        raise ValueError(f"DOCX text extraction failed: {e}")


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract text from file bytes based on file extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext in ("docx", "doc"):
        return extract_text_from_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type for text extraction: {ext}")


class InAppParsingService:
    """Service for AI document parsing using OpenAI via Replit AI Integrations."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.pipeline_service = ExtractionPipelineService(db_session)
        self.ai_results_crud = AIParsingResultCRUD(db_session)
        self._openai_client = None

    @property
    def openai_client(self):
        """Lazy-initialize OpenAI client using Replit AI Integrations."""
        if self._openai_client is None:
            try:
                from openai import OpenAI
                api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
                base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
                if not api_key or not base_url:
                    raise ValueError(
                        "AI_INTEGRATIONS_OPENAI_API_KEY and AI_INTEGRATIONS_OPENAI_BASE_URL must be set. "
                        "Install the OpenAI integration via Replit AI Integrations."
                    )
                self._openai_client = OpenAI(api_key=api_key, base_url=base_url)
                logger.info("OpenAI client initialized via Replit AI Integrations")
            except ImportError as e:
                raise RuntimeError("openai package not installed") from e
        return self._openai_client

    def download_file_bytes(self, file: FileModel) -> bytes:
        """Download file bytes from storage."""
        storage_service = get_storage_service()
        if file.storage_key:
            logger.info(f"Downloading file from Replit storage: {file.storage_key}")
            return storage_service.download_bytes(file.storage_key)
        elif file.filepath:
            logger.warning(f"File {file.id} uses legacy GCS path - not supported in Replit-native mode")
            raise ValueError(
                f"File {file.id} uses legacy GCS storage. "
                "Re-upload the file to use Replit Object Storage."
            )
        else:
            raise ValueError(f"File {file.id} has no storage_key or filepath")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception(is_rate_limit_error),
        reraise=True,
    )
    def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        model_name: str = "gpt-5.2",
        max_tokens: int = 8192,
    ) -> dict:
        """Call OpenAI API with retry logic for rate limits."""
        # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
        # do not change this unless explicitly requested by the user
        model = model_name if model_name else "gpt-5.2"
        if model.startswith("gpt-4") and not model.startswith("gpt-4.1"):
            model = "gpt-5.2"
        logger.info(f"Calling LLM with model: {model}")
        response = self.openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {content[:500]}")
            raise ValueError(f"LLM response is not valid JSON: {e}")

    def parse_file(
        self,
        file: FileModel,
        ai_result_id: int,
        document_type_name: str,
        correlation_id: Optional[str] = None,
    ) -> dict:
        """
        Parse a file and update the AIParsingResult record.

        Args:
            file: The File model instance
            ai_result_id: ID of the AIParsingResult record to update
            document_type_name: Document type name for extraction config lookup
            correlation_id: Optional correlation ID for logging/tracing

        Returns:
            dict with parsed result and metadata
        """
        correlation_id = correlation_id or str(uuid.uuid4())[:8]
        log_prefix = f"[{correlation_id}] File {file.id}"
        logger.info(f"{log_prefix} Starting in-app parsing for document type: {document_type_name}")
        start_time = datetime.now(timezone.utc)
        retries = 0

        try:
            file_bytes = self.download_file_bytes(file)
            logger.info(f"{log_prefix} Downloaded {len(file_bytes)} bytes")
            document_text = extract_text(file_bytes, file.filename)
            logger.info(f"{log_prefix} Extracted {len(document_text)} characters of text")
            if len(document_text) < 50:
                raise ValueError(f"Extracted text too short ({len(document_text)} chars) - possibly empty document")
            prompt_data = self.pipeline_service.build_extraction_prompt(document_type_name, document_text)
            if not prompt_data:
                raise ValueError(f"No extraction config found for document type: {document_type_name}")
            logger.info(
                f"{log_prefix} Built extraction prompt with "
                f"doc_type_id={prompt_data['metadata']['document_type_id']}, "
                f"schema_v={prompt_data['metadata']['schema_version_id']}, "
                f"prompt_v={prompt_data['metadata']['prompt_template_id']}"
            )
            parsed_result = self.call_llm(
                system_prompt=prompt_data["system_prompt"],
                user_prompt=prompt_data["user_prompt"],
                model_name=prompt_data["model_config"]["model_name"],
                max_tokens=prompt_data["model_config"]["max_tokens"] or 8192,
            )
            logger.info(f"{log_prefix} LLM extraction completed, {len(parsed_result)} fields extracted")
            end_time = datetime.now(timezone.utc)
            self.ai_results_crud.update_by_id(ai_result_id, {
                "status": FileParsingStatuses.completed,
                "parsed_result": parsed_result,
                "end_time": end_time,
                "document_type_id": prompt_data["metadata"]["document_type_id"],
                "schema_version_id": prompt_data["metadata"]["schema_version_id"],
                "prompt_template_id": prompt_data["metadata"]["prompt_template_id"],
                "retries": retries,
                "error_message": None,
            })
            logger.info(f"{log_prefix} Parsing completed successfully in {(end_time - start_time).total_seconds():.2f}s")
            return {
                "status": "completed",
                "parsed_result": parsed_result,
                "metadata": prompt_data["metadata"],
                "duration_seconds": (end_time - start_time).total_seconds(),
            }

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            error_msg = str(e)[:500]
            logger.error(f"{log_prefix} Parsing failed: {error_msg}")
            self.ai_results_crud.update_by_id(ai_result_id, {
                "status": FileParsingStatuses.processing_failed,
                "end_time": end_time,
                "error_message": error_msg,
                "retries": retries,
            })
            raise

    def check_openai_available(self) -> bool:
        """Check if OpenAI integration is properly configured.
        
        Validates both environment variables and ability to instantiate client.
        """
        api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
        base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
        if not api_key or not base_url:
            return False
        try:
            from openai import OpenAI
            OpenAI(api_key=api_key, base_url=base_url)
            return True
        except Exception as e:
            logger.warning(f"OpenAI client instantiation failed: {e}")
            return False


def get_in_app_parsing_service(db_session: Session) -> InAppParsingService:
    """Factory function for dependency injection."""
    return InAppParsingService(db_session)
