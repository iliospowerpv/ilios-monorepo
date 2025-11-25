import pytest
from langchain.text_splitter import TextSplitter
from langchain_core.embeddings import Embeddings

from src.vectordb.vectordb import VectorDB


@pytest.fixture
def vector_db() -> VectorDB:
    """Return a VectorDB object."""
    vector_db = VectorDB()
    return vector_db


def test_init() -> None:
    """Test the initialization of the VectorDB class."""
    vector_db = VectorDB(
        k=10,
        chunk_size=600,
        add_tables=True,
    )
    assert isinstance(vector_db.text_splitter, TextSplitter)
    assert isinstance(vector_db.embeddings, Embeddings)
    assert vector_db.k == 10
    assert vector_db.chunk_size == 600
    assert vector_db.add_tables is True


def test_get_embeddings(vector_db: VectorDB) -> None:
    """Test the get_embeddings method."""
    embeddings = vector_db.get_embeddings()
    assert isinstance(embeddings, Embeddings)


def test_get_text_splitter(vector_db: VectorDB) -> None:
    """Test the get_text_splitter method."""
    text_splitter = vector_db.get_text_splitter()
    assert isinstance(text_splitter, TextSplitter)
