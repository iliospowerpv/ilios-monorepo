import logging
from pathlib import Path
from typing import Iterator, List, Optional

from google.api_core.client_options import ClientOptions
from google.cloud import documentai
from google.cloud.documentai_v1 import ProcessOptions

from src.doc_ai.document_sequence import DocumentSequence
from src.doc_ai.file import File
from src.doc_ai.file_sequence import FileSequence


logger = logging.getLogger(__name__)


class DocAIProcessor:
    """Class used to process documents using the Document AI API."""

    def __init__(
        self,
        project_id: str,
        location: str,
        processor_id: str,
        processor_version_id: Optional[str] = None,
    ):
        self.project_id: str = project_id
        self.location: str = location
        self.processor_id: str = processor_id
        self.processor_version_id: Optional[str] = processor_version_id
        self.client_options = ClientOptions(
            api_endpoint=f"{self.location}-documentai.googleapis.com"
        )
        self.client = documentai.DocumentProcessorServiceClient(
            client_options=self.client_options
        )
        self.processor_name: str = self.get_processor_name()
        self.processed_doc_history: List[FileSequence] = []
        self.DOC_AI_API_PAGE_LIMIT = 15
        self.DOCUMENT_SIZE_LIMIT = 20000000

    def get_processor_name(self) -> str:
        """Define and setup Document AI processor"""
        if self.processor_version_id:
            processor_name = self.client.processor_version_path(
                self.project_id,
                self.location,
                self.processor_id,
                self.processor_version_id,
            )
        else:
            processor_name = self.client.processor_path(
                self.project_id, self.location, self.processor_id
            )
        return processor_name

    @staticmethod
    def get_process_options(pages: List[int]) -> ProcessOptions:
        """Define the process options for the Document AI processor"""
        process_options = ProcessOptions(
            individual_page_selector=ProcessOptions.IndividualPageSelector(pages=pages)
        )
        return process_options

    def process_document(
        self,
        file_path: str | Path,
        mime_type: str = "application/pdf",
        field_mask: Optional[str] = None,
        pages: Optional[list[int]] = None,
    ) -> File:
        """
        Process a single document with the given processor.

        :param file_path: The absolute path to the file to process, local or GCS bucket.
            Could be also a bytes object.
        :param mime_type: The mime type of the file, e.g. "application/pdf".
        :param field_mask: The field mask to be used for processing.
        :param pages: The pages to be processed. If None, all pages will be processed.
        """

        logger.info("DocAIProcessor.process_document start")
        try:
            logger.info("CREATING FILE OBJECT")
            file: File = File(path=file_path, pages=pages)
        except Exception as e:
            raise ValueError(f"Failed to create File object. Error: {e}")
        processed_document_chunks: DocumentSequence = DocumentSequence(documents=[])
        logger.info("PREPARING DOCUMENT BATCHES")
        page_sizes: List[int] = file.get_pdf_page_sizes()
        batches: List[List[int]] = list(self.create_batches(page_sizes, file.all_pages))
        for batch in batches:
            logger.info(
                f"BATCH SIZE: "
                f"{sum([page_sizes[i] for i in batch])}"  # noqa
            )
            try:
                raw_document = documentai.RawDocument(
                    content=file.get_pages(batch), mime_type=mime_type
                )
            except Exception as e:
                raise ValueError(
                    f"Failed to create Document AI RawDocument object. Error: {e}"
                )
            try:
                request = documentai.ProcessRequest(
                    name=self.processor_name,
                    raw_document=raw_document,
                    field_mask=field_mask,
                    process_options=None,
                )
                processed_document_chunks.append(
                    self.client.process_document(request=request).document
                )
            except Exception:
                logger.info(f"Failed to process pages {batch}")
                continue
        file.add_docai_representation(processed_document_chunks)
        return file

    def create_batches(
        self, page_sizes: List[int], page_nums: List[int]
    ) -> Iterator[List[int]]:
        """Create batches of pages to process"""
        batch: List[int] = []
        batch_size = 0
        for page_num in page_nums:
            page_size = page_sizes[page_num]
            if (
                batch_size + page_size > self.DOCUMENT_SIZE_LIMIT
                or len(batch) >= self.DOC_AI_API_PAGE_LIMIT
            ):
                yield batch
                batch = [page_num]
                batch_size = page_size
            else:
                batch.append(page_num)
                batch_size += page_size
        yield batch

    def check_size(self, page_sizes: List[float]) -> bool:
        """Check condition: if the pages exceed 20MB DocumentAI limit"""
        if sum(page_sizes) >= self.DOCUMENT_SIZE_LIMIT:
            return True
        else:
            return False

    def check_num_of_pages(self, pages: List[int]) -> bool:
        """Check condition: if the pages exceed 15 pages DocumentAI limit"""
        if len(pages) > self.DOC_AI_API_PAGE_LIMIT:
            return True
        else:
            return False

    def process_documents(
        self,
        document_list: List[str | Path],
        mime_type: str = "application/pdf",
        field_mask: Optional[str] = None,
        pages: Optional[List[List[int]]] = None,
    ) -> FileSequence:
        """
        Process multiple documents with the given processor.
        :param document_list:
        :param mime_type: type of the file to process
        :param field_mask: field mask if relevant
        :param pages: specific pages numbers if needed
        :return: List of Documents
        """
        if pages:
            assert len(document_list) == len(
                pages
            ), "Number of pages must match number of documents"
            files = FileSequence(
                [
                    self.process_document(
                        file_path=document,
                        mime_type=mime_type,
                        field_mask=field_mask,
                        pages=document_pages,
                    )
                    for document, document_pages in zip(document_list, pages)
                ]
            )
            self.processed_doc_history.append(files)
            return files
        else:
            files = FileSequence(
                [
                    self.process_document(
                        file_path=document,
                        mime_type=mime_type,
                        field_mask=field_mask,
                    )
                    for document in document_list
                ]
            )
            self.processed_doc_history.append(files)
            return files

    def get_full_text(self, file_id: int = -1) -> str:
        """
        Return the text of the file based on the index. Default - last processed
        file.
        """
        return self.processed_doc_history[file_id].get_all_text()
