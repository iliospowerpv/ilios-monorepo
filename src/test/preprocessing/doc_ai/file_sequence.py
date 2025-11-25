import pytest

from src.doc_ai.file import File
from src.doc_ai.file_sequence import FileSequence


@pytest.fixture
def file_sequence_obj(file_obj: File) -> FileSequence:
    """Create a FileSequence object with a single document"""
    return FileSequence([file_obj])


@pytest.mark.parametrize("index, expected_name", [(0, "test_file.txt")])
def test_file_sequence_index(
    file_sequence_obj: FileSequence, index: int, expected_name: str
) -> None:
    """Test that the __getitem__ method returns the correct document at the given
    index"""
    assert file_sequence_obj[index].name == expected_name


def test_file_sequence_len(file_sequence_obj: FileSequence) -> None:
    """Test that the __len__ method returns the correct number of documents"""
    assert len(file_sequence_obj) == 1


def test_file_sequence_get_all_text(file_sequence_obj: FileSequence) -> None:
    """Test that the get_all_text method returns the text of all the documents in the
    sequence"""
    assert file_sequence_obj.get_all_text() == file_sequence_obj[0].get_all_text()
