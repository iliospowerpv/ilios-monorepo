import pytest

from app.crud.comment import CommentCRUD
from app.settings import settings


class TestInternal:
    INTERNAL_PATH = "/api/internal"
    COMMENTS_ENDPOINT = f"{INTERNAL_PATH}/comments"

    def test_delete_comment(self, client, comment, db_session):
        comment_id = comment.id
        response = client.delete(f"{self.COMMENTS_ENDPOINT}/{comment_id}", params={"api_key": settings.api_key})
        assert response.status_code == 204

        db_session.expunge(comment)  # unload item from the session mapping, so new instance can be re-fetched for test
        assert CommentCRUD(db_session).get_by_id(comment_id) is None

    @pytest.mark.parametrize(
        "api_key, expected_status_code",
        (
            (settings.api_key, 404),
            ("WRONG_API_KEY", 403),
        ),
    )
    def test_delete_role_negative(self, client, api_key, expected_status_code):
        """Test negative cases are caught and handled appropriately"""
        response = client.delete(f"{self.COMMENTS_ENDPOINT}/99999", params={"api_key": api_key})
        assert response.status_code == expected_status_code
