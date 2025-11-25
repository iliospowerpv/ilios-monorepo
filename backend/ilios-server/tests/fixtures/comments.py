import pytest

from app.crud.comment import CommentCRUD
from app.crud.commented_entity import CommentedEntityCRUD


@pytest.fixture(scope="function", params=["Dummy comment about something completely different"])
def comment(request, db_session, document):
    comment_text = request.param
    comment_crud, commented_entity_crud = CommentCRUD(db_session), CommentedEntityCRUD(db_session)

    comment = comment_crud.create_item({"text": comment_text, "user_id": None})
    commented_entity_crud.create_item({"entity_id": document.id, "entity_type": "document", "comment_id": comment.id})

    yield comment

    comment_crud.delete_by_id(comment.id)  # related entities will be removed by cascade
