import pytest
from google.cloud.documentai_v1 import Document

from src.doc_ai.document_sequence import DocumentSequence


@pytest.fixture
def document() -> Document:
    """Create a mock Document object"""
    doc = Document()
    doc.text = "Test document text"
    return doc


def test_init(document: Document) -> None:
    """Test that the __init__ method correctly sets the documents attribute"""
    ds = DocumentSequence([document])
    assert len(ds.documents) == 1
    assert ds.documents[0] == document


def test_len(document: Document) -> None:
    """Test that the __len__ method correctly returns the number of documents"""
    ds = DocumentSequence([document])
    assert len(ds) == 1


def test_append(document: Document) -> None:
    """Test that the append method correctly adds a document"""
    ds = DocumentSequence([])
    ds.append(document)
    assert len(ds) == 1
    assert ds.documents[0] == document


def test_get_all_text(document: Document) -> None:
    """Test that the get_all_text method correctly returns the text of all documents"""
    ds = DocumentSequence([document])
    assert ds.get_all_text() == "Test document text"


def test_get_paragraphs(document: Document) -> None:
    """
    Test that the get_paragraphs method correctly returns the paragraphs of all
    documents
    """
    ds = DocumentSequence([document])
    assert ds.get_paragraphs() == []
