from collections.abc import Sequence
from itertools import chain
from typing import Any, List, Union, overload

from src.doc_ai.file import File


class FileSequence(Sequence[File]):
    """File is defined as per whole raw file. FileSequence could be SiteLease plus
    amendments, etc. It is designed to pack the related information together."""

    @overload
    def __getitem__(self, index: int) -> File:
        """Return the document at the given index"""
        return self.documents[index]

    @overload
    def __getitem__(self, index: slice) -> Sequence[File]:
        """Return the documents at the given slice"""
        return self.documents[index]

    def __getitem__(self, index: Union[int, slice]) -> Union[File, Sequence[File]]:
        """Return the document at the given index or the documents at the given slice"""
        return self.documents[index]

    def __init__(self, documents: List[File]) -> None:
        """Initializes the DocumentSequence with a list of documents"""
        self.documents = documents

    def __len__(self) -> int:
        """Returns the number of documents in the sequence"""
        return len(self.documents)

    def get_all_text(self) -> str:
        """Returns the text of all the documents"""
        return "\n\n".join([doc.get_all_text() for doc in self.documents])

    def get_tables(self) -> list[Any]:
        """Returns the tables of all the documents"""
        return list(chain.from_iterable([doc.get_tables() for doc in self.documents]))

    def get_form_fields(self) -> list[Any]:
        """Returns the form fields of all the documents"""
        return list(
            chain.from_iterable([doc.get_form_fields() for doc in self.documents])
        )

    def get_paragraphs(self) -> list[Any]:
        """Returns the paragraphs of all the documents"""
        return list(
            chain.from_iterable([doc.get_paragraphs() for doc in self.documents])
        )

    def get_blocks(self) -> list[Any]:
        """Returns the blocks of all the documents"""
        return list(chain.from_iterable([doc.get_blocks() for doc in self.documents]))
