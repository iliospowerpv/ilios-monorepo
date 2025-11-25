from typing import Optional

from sqlalchemy.orm import Session

from app.helpers.configs.ai_parsing_helper import AIParsingHandler
from app.models.document import Document
from app.models.file import File as FileModel
from app.models.file import FileParsingStatuses
from app.schema.file import FileKeySchema


def combine_user_ai_parsing_results(
    document: Document, db_session: Session, due_diligence_file: Optional[FileModel] = None
):
    """
    Function combines results received from AI that is unique per each file and stored in File object with document
    level keys and values created by User that are common for all files in a section.

    E.g.: All files from site_lease section will have their AI parsing result values + site_lease key document values.
    """
    document_available_keys = [
        FileKeySchema(name=key).model_dump()
        for key in AIParsingHandler(db_session).get_keys_by_document_type(document.name.value)
    ]
    if not document_available_keys:
        return document_available_keys

    # Get data stored in DB from user and AI
    existing_user_keys = {
        key.name: {"value": key.value, "updated_at": key.updated_at, "id": key.id} for key in document.keys
    }
    # ensure parsing record exists, parsing status is 'completed' and result is not empty
    ai_parsing_result = (
        due_diligence_file.latest_ai_result.result
        if due_diligence_file
        and due_diligence_file.latest_ai_result
        and due_diligence_file.latest_ai_result.status == FileParsingStatuses.completed
        and due_diligence_file.latest_ai_result.result
        else []
    )
    existing_ai_keys = {
        key["key_item"]: {
            "ai_value": key["value"],
            "poison_pill": key["poison_pill"],
            "poison_pill_detailed": key["poison_pill_detailed"],
            # cast to bool since AI respond with 0/1
            "is_poison_pill": bool(key.get("is_poison_pill", False)),
            "legal_term": key["legal_term"],
        }
        for key in ai_parsing_result
    }

    for available_key in document_available_keys:
        # Update with data stored in DB
        if existing_user_keys.get(available_key["name"]):
            available_key.update(existing_user_keys.get(available_key["name"]))

        if existing_ai_keys.get(available_key["name"]):
            available_key.update(existing_ai_keys.get(available_key["name"]))

    return document_available_keys
