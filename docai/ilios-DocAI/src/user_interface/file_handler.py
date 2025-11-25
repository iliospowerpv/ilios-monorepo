import io
from pathlib import Path
from typing import List, Optional

from docx2pdf import convert
from pypdf import PdfReader, PdfWriter
from streamlit.runtime.uploaded_file_manager import UploadedFile

from src.settings import PROJECT_ROOT_PATH
from src.user_interface.doc_type import DocType


class StreamlitFileHandler:
    def __init__(
        self,
        documents: List[UploadedFile] | None,
        data_folder: Optional[str | Path] = None,
    ) -> None:
        """Initialize StreamlitFileHandler with a list of files."""
        if data_folder and not isinstance(data_folder, Path):
            self.data_folder = Path(data_folder)
        if not data_folder:
            self.data_folder = PROJECT_ROOT_PATH / "data" / "documents"
        if documents is None:
            raise ValueError("No documents uploaded.")
        else:
            self.documents = documents
            self.document_names = [document.name for document in documents]

    def classify_documents(self) -> List[DocType]:
        """Classify documents based on their file extensions."""
        doc_types = []
        for document in self.document_names:
            if document.lower().endswith(".pdf"):
                doc_types.append(DocType.PDF)
            elif document.lower().endswith(".docx"):
                doc_types.append(DocType.DOCX)
            else:
                raise ValueError(f"Unsupported file format: {document}")
        return doc_types

    def _save_pdf(self, uploaded_file: UploadedFile) -> Path:
        """Save PDF to local storage."""
        file_path = self.data_folder / f"{uploaded_file.name}"
        bytes_data = uploaded_file.getvalue()
        result_pdf = PdfWriter()

        pdf = PdfReader(
            stream=io.BytesIO(initial_bytes=bytes_data)  # Create steam object
        )
        for page in range(len(pdf.pages)):
            result_pdf.add_page(pdf.pages[page])

        result_pdf.write(file_path)
        return file_path

    def _save_docx(self, uploaded_file: UploadedFile) -> Path:
        """Save DOCX to local storage as PDF."""
        file_path = self.data_folder / f"{uploaded_file.name}".replace(".docx", ".pdf")
        docx_bytes = uploaded_file.getvalue()
        docx_path = "/tmp/temp.docx"
        with open(docx_path, "wb") as f:
            f.write(docx_bytes)
        convert(docx_path, file_path)

        return file_path

    def save_files(self) -> List[Path]:
        """Get files from user input."""
        file_types = self.classify_documents()
        files = []
        if self.documents is not None:
            for uploaded_file, doc_type in zip(self.documents, file_types):
                if doc_type == DocType.PDF:
                    files.append(self._save_pdf(uploaded_file))
                elif doc_type == DocType.DOCX:
                    files.append(self._save_docx(uploaded_file))
        return files

    def read_files_to_bytes(self) -> List[bytes]:
        """Reads uploaded files straight to bytes format to be consumed by document
        AI processor."""
        return [uploaded_file.getvalue() for uploaded_file in self.documents]
