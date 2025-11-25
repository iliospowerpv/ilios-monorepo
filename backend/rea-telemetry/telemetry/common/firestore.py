from collections.abc import Iterator
from typing import Any, NamedTuple

from google.cloud import firestore

from .constants import PROJECT_ID
from .thread_local import ThreadLocalProxy


class Document(NamedTuple):
    id: str
    data: dict[str, Any]


class Database:

    def __init__(self) -> None:
        self._client = firestore.Client(project=PROJECT_ID)

    def collection(self, collection_id: str) -> firestore.CollectionReference:
        return self._client.collection(collection_id)

    def document(self, collection_id: str, document_id: str) -> firestore.DocumentReference:
        return self._client.document(collection_id, document_id)

    def stream_documents(self, collection_id: str) -> Iterator[Document]:
        for document in self.collection(collection_id).stream():
            if document.exists:
                yield Document(id=document.id, data=document.to_dict())

    def get_document(self, collection_id: str, document_id: str) -> Document | None:
        document = self.document(collection_id, document_id).get()
        return Document(id=document.id, data=document.to_dict()) if document.exists else None

    def set_document(self, collection_id: str, document_id: str, document_data: dict[str, Any]) -> None:
        self.document(collection_id, document_id).set(document_data)


database = ThreadLocalProxy(Database)
