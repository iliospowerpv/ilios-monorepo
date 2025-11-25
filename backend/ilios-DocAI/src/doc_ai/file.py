import io
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz
import google.cloud.storage as storage
from PyPDF2 import PdfReader, PdfWriter

from src.doc_ai.document_sequence import DocumentSequence
from src.user_interface.doc_type import DocType


logger = logging.getLogger(__name__)


class File:
    def __init__(self, path: str | Path, pages: List[int] | None) -> None:
        """Initialize the File class."""
        self.path: str | Path = path
        self.name: str = os.path.basename(self.path)
        self.doc_type: DocType = self._get_doc_type()
        try:
            self.bytes_repr: bytes = self._read_file()
            self.reader = PdfReader(io.BytesIO(self.bytes_repr), strict=False)
        except Exception as e:
            logger.error(f"Failed to read bytes from {self.path}. Error: {e}")
            raise ValueError(f"Failed to read file from {self.path}. Error:{e}")

        self.is_uploaded: bool = True
        self.all_pages: List[int] = self._get_num_pages(pages)
        self.is_processed: bool = False
        self.doc_ai_repr: Optional[DocumentSequence] = None
        self.metadata: Optional[Dict[str, Any]] = None

    def _read_file(self) -> bytes:
        """Read document from the source"""
        logger.info(f"Reading {self.doc_type} file: %s", self.path)
        if isinstance(self.path, Path):
            self.path = str(self.path)
        try:
            if self.path.startswith("gs://"):
                logger.info("Reading file from gs bucket %s", self.path)
                storage_client = storage.Client()
                split_path = self.path.split("gs://")[1].split("/")
                bucket_name, blob_name = split_path[0], "/".join(split_path[1:])
                bucket = storage_client.get_bucket(bucket_name)
                blob = bucket.blob(blob_name)
                image_content: bytes = blob.download_as_bytes()
            else:
                logger.info("Reading file from local path %s", self.path)
                with open(self.path, "rb") as image:
                    image_content = image.read()
        except Exception as e:
            raise ValueError(f"Failed to read file from {self.path}. Error: {e}")
        return image_content

    def get_pages(self, pages: List[int]) -> bytes:
        """Returns only the pages specified in the list."""
        logger.info(f"Pages: {pages}")
        assert (
            self.doc_type == DocType.PDF
        ), "Only PDF files are supported for the read method"
        logger.info("Extracting pages: %s", pages)
        try:
            pdf_writer = PdfWriter()
            for page in pages:
                pdf_writer.add_page(self.reader.pages[page])
            image_content = io.BytesIO()
            pdf_writer.write(image_content)
            image_content.seek(0)
            image_content = image_content.read()  # type: ignore
        except Exception as e:
            logger.info(
                f"PDFReader failed to extract pages {pages} from {self.name}. "
                f"Error: {e}"
            )
            raise ValueError(
                f"PDFReader failed to extract pages {pages} from {self.name}. "
                f"Error: {e}"
            )
        return image_content  # type: ignore

    def get_pdf_page_size(self, page_number: int) -> int:
        """Get the size of a specific PDF page in bytes."""
        writer = PdfWriter()
        writer.add_page(self.reader.pages[page_number])
        output = io.BytesIO()
        writer.write(output)
        return len(output.getvalue())

    def get_pdf_page_sizes(self) -> List[int]:
        """Get the sizes of all PDF pages in bytes."""
        return [self.get_pdf_page_size(i) for i, _ in enumerate(self.reader.pages)]

    def _get_doc_type(self) -> DocType:
        """Classify documents based on their file extensions."""
        if self.name.lower().endswith(".pdf"):
            return DocType.PDF
        elif self.name.lower().endswith(".docx"):
            return DocType.DOCX
        else:
            raise ValueError(f"Unsupported file format: {self.name}")

    def _get_num_pages(self, pages: List[int] | None) -> List[int]:
        with fitz.open(stream=io.BytesIO(self.bytes_repr), filetype="pdf") as f:
            try:
                original_pages = [i for i in range(0, len(list(f.pages())))]
                logger.info(f"Number of pages in {self.path}: {len(original_pages)}")
            except Exception as e:
                logger.error(
                    f"Failed to get number of pages from {self.path} "
                    f"with PyMuPdf. Error: {e}"
                )
                raise ValueError(
                    f"Failed to get number of pages from {self.path} "
                    f"with PyMuPdf. Error: {e}"
                )
        if pages is None:
            return original_pages
        else:
            return [page for page in pages if page < len(original_pages)]

    def get_all_text(self) -> str:
        """Return the text of the document."""
        if self.is_processed:
            return self.doc_ai_repr.get_all_text()  # type: ignore
        else:
            raise ValueError("Document has not been processed yet.")

    def get_tables(self) -> str:
        """Return tables of the document."""
        if self.is_processed:
            return self.doc_ai_repr.get_tables()  # type: ignore
        else:
            raise ValueError("Document has not been processed yet.")

    def get_form_fields(self) -> str:
        """Return form fields of the document."""
        if self.is_processed:
            return self.doc_ai_repr.get_form_fields()  # type: ignore
        else:
            raise ValueError("Document has not been processed yet.")

    def get_paragraphs(self) -> List[str]:
        """Return the paragraphs of the document."""
        if self.is_processed:
            return self.doc_ai_repr.get_paragraphs()  # type: ignore
        else:
            raise ValueError("Document has not been processed yet.")

    def get_blocks(self) -> List[str]:
        """Return the paragraphs of the document."""
        if self.is_processed:
            return self.doc_ai_repr.get_blocks()  # type: ignore
        else:
            raise ValueError("Document has not been processed yet.")

    def add_docai_representation(self, docai_representation: DocumentSequence) -> None:
        """Add the DocumentSequence representation of the document."""
        self.doc_ai_repr = docai_representation
        self.is_processed = True
