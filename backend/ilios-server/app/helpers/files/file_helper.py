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
    # Get extraction config with both name and display_name for proper matching
    from app.services.extraction_pipeline_service import ExtractionPipelineService
    
    handler = AIParsingHandler(db_session)
    config = handler.get_extraction_config(document.name.value)
    
    # Build mapping from canonical name to display_name, and prepare available keys
    name_to_display = {}
    if config and config.get("fields"):
        for f in config["fields"]:
            name_to_display[f["name"]] = f["display_name"]
    
    document_available_keys = [
        FileKeySchema(name=display_name).model_dump()
        for display_name in handler.get_keys_by_document_type(document.name.value)
    ]
    if not document_available_keys:
        return document_available_keys
    
    # Build reverse mapping: display_name -> canonical name
    display_to_name = {v: k for k, v in name_to_display.items()}

    existing_user_keys = {
        key.name: {
            "value": key.value,
            "updated_at": key.updated_at,
            "id": key.id,
            "is_poison_pill": key.is_poison_pill,
            "poison_pill_detailed": key.poison_pill_notes,
        }
        for key in document.keys
    }
    # ensure parsing record exists, parsing status is 'completed' and result is not empty
    ai_parsing_result = []
    if (
        due_diligence_file
        and due_diligence_file.latest_ai_result
        and due_diligence_file.latest_ai_result.status == FileParsingStatuses.completed
    ):
        latest = due_diligence_file.latest_ai_result
        # Check for new format (parsed_result with fields array) first
        if latest.parsed_result and isinstance(latest.parsed_result, dict):
            fields = latest.parsed_result.get("fields", [])
            # Convert new format to old format for compatibility
            ai_parsing_result = [
                {
                    "key_item": f.get("field_key", ""),
                    "value": f.get("value"),
                    "poison_pill": None,
                    "poison_pill_detailed": None,
                    "is_poison_pill": False,
                    "legal_term": None,
                    "evidence": f.get("evidence"),  # preserve evidence for display
                }
                for f in fields
            ]
        # Fallback to old format (result column)
        elif latest.result:
            ai_parsing_result = latest.result
    
    existing_ai_keys = {
        key["key_item"]: {
            "ai_value": key["value"],
            "poison_pill": key.get("poison_pill"),
            "poison_pill_detailed": key.get("poison_pill_detailed"),
            # cast to bool since AI respond with 0/1
            "is_poison_pill": bool(key.get("is_poison_pill", False)),
            "legal_term": key.get("legal_term"),
            "evidence": key.get("evidence"),  # include evidence if available
        }
        for key in ai_parsing_result
    }

    for available_key in document_available_keys:
        display_name = available_key["name"]
        canonical_name = display_to_name.get(display_name, "")

        if existing_user_keys.get(display_name):
            available_key.update(existing_user_keys.get(display_name))

        if canonical_name and existing_ai_keys.get(canonical_name):
            available_key.update(existing_ai_keys.get(canonical_name))

        user_data = existing_user_keys.get(display_name)
        if user_data and "is_poison_pill" in user_data:
            available_key["is_poison_pill"] = user_data["is_poison_pill"]
            if user_data.get("poison_pill_detailed") is not None:
                available_key["poison_pill_detailed"] = user_data["poison_pill_detailed"]

    return document_available_keys
