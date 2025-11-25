import pytest

from src.doc_ai.file import File


@pytest.fixture
def file_obj() -> File:
    """Create a File object with a list of pages"""
    return File("test_file.txt", [1, 2, 3])


def test_file_name(file_obj: File) -> None:
    """Test that the name attribute is set correctly"""
    assert file_obj.name == "test_file.txt"


def test_file_size(file_obj: File) -> None:
    """Test that the size attribute is set correctly"""
    assert file_obj.all_pages == [1, 2, 3]
