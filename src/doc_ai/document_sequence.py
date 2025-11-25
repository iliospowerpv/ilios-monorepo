from collections.abc import Sequence
from itertools import chain
from typing import Dict, List, Union, overload

from google.cloud import documentai
from google.cloud.documentai_v1 import Document

from src.doc_ai.utils import get_form_fields, get_tables


class DocumentSequence(Sequence[Document]):
    """Object used to structure the output from the Document AI API, where longer
    documents have been split into multiple documents. This class allows for easy
    access to the text of all the documents and the paragraphs of each document.
    DocumentSequence is one document like SiteLease split into chunks of ~15 pages"""

    class Config:
        arbitrary_types_allowed = True

    @overload
    def __getitem__(self, index: int) -> Document:
        """Return the document at the given index"""
        return self.documents[index]

    @overload
    def __getitem__(self, index: slice) -> Sequence[Document]:
        """Return the documents at the given slice"""
        return self.documents[index]

    def __getitem__(
        self, index: Union[int, slice]
    ) -> Union[Document, Sequence[Document]]:
        """Return the document at the given index or the documents at the given slice"""
        return self.documents[index]

    def __init__(self, documents: List[Document]) -> None:
        """Initializes the DocumentSequence with a list of documents"""
        self.documents = documents

    def __len__(self) -> int:
        """Returns the number of documents in the sequence"""
        return len(self.documents)

    def append(self, document: Document) -> None:
        """Adds a document to the sequence of documents"""
        self.documents.append(document)

    def get_all_text(self) -> str:
        """Returns the text of all the documents"""
        all_text = "\n".join([doc.text for doc in self.documents])
        return all_text

    def get_tables(self) -> List[str]:
        """Returns the list of all the tables in the documents as strings."""
        parsed_tables = [get_tables(document).values() for document in self.documents]
        return list(chain.from_iterable(list(chain.from_iterable(parsed_tables))))

    def get_form_fields(self) -> List[Dict[str, str]]:
        """Returns the list of all the tables in the documents as strings."""
        parsed_tables = [
            get_form_fields(document).values() for document in self.documents
        ]
        return list(chain.from_iterable(parsed_tables))

    @staticmethod
    def layout_to_text(layout: documentai.Document.Page.Layout, text: str) -> str:
        """
        Document AI identifies text in different parts of the document by their
        offsets in the entirety of the document's text. This function converts
        offsets to a string.
        """
        return "".join(
            text[int(segment.start_index) : int(segment.end_index)]
            for segment in layout.text_anchor.text_segments
        )

    def _get_page_paragraphs_text(
        self, paragraphs: Sequence[documentai.Document.Page.Paragraph], text: str
    ) -> List[str]:
        """Returns the text in the paragraphs for one page"""
        return [self.layout_to_text(paragraph.layout, text) for paragraph in paragraphs]

    def _get_page_blocks_text(
        self, blocks: Sequence[documentai.Document.Page.Block], text: str
    ) -> List[str]:
        """Returns the text in the paragraphs for one page"""
        return [self.layout_to_text(block.layout, text) for block in blocks]

    def _get_document_paragraphs(self, document: Document) -> Dict[int, List[str]]:
        """Return Dict with page number as key and list of paragraphs as value."""
        return {
            page.page_number: self._get_page_paragraphs_text(
                page.paragraphs, document.text
            )
            for page in document.pages
        }

    def _get_document_blocks(self, document: Document) -> Dict[int, List[str]]:
        """Return Dict with page number as key and list of paragraphs as value."""
        return {
            page.page_number: self._get_page_blocks_text(page.blocks, document.text)
            for page in document.pages
        }

    def get_paragraphs(self) -> List[str]:
        """
        Returns the text in the paragraphs of the document. When no document is
        provided, the last processed document is used.
        """
        """Returns the list of all the tables in the documents as strings."""
        parsed_paragraphs = [
            paragraph
            for document in self.documents
            for paragraph in self._get_document_paragraphs(document).values()
        ]
        return list(chain.from_iterable(parsed_paragraphs))

    def get_blocks(self) -> List[str]:
        """
        Returns the text in the blocks of the document. When no document is
        provided, the last processed document is used.
        """
        """Returns the list of all the tables in the documents as strings."""
        parsed_blocks = [
            paragraph
            for document in self.documents
            for paragraph in self._get_document_blocks(document).values()
        ]
        return list(chain.from_iterable(parsed_blocks))
