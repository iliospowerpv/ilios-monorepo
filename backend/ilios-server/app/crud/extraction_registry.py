"""CRUD operations for Extraction Registry

Provides database operations for document types, schema versions, and prompt templates.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.crud.base_crud import BaseCRUD
from app.models.extraction_registry import (
    ExtractionDocumentType,
    ExtractionSchemaVersion,
    ExtractionSchemaVersionField,
    ExtractionPromptTemplate,
)
from app.models.project_facts import CanonicalField


class ExtractionDocumentTypeCRUD(BaseCRUD):
    def __init__(self, db_session: Session):
        super().__init__(ExtractionDocumentType, db_session)

    def get_by_name(self, name: str) -> Optional[ExtractionDocumentType]:
        return self.db_session.query(ExtractionDocumentType).filter(
            ExtractionDocumentType.name == name
        ).first()

    def get_active_types(self) -> List[ExtractionDocumentType]:
        return self.db_session.query(ExtractionDocumentType).filter(
            ExtractionDocumentType.is_active == True
        ).order_by(ExtractionDocumentType.display_name).all()

    def get_parsable_types(self) -> List[ExtractionDocumentType]:
        return self.db_session.query(ExtractionDocumentType).filter(
            ExtractionDocumentType.is_active == True,
            ExtractionDocumentType.is_parsable == True
        ).order_by(ExtractionDocumentType.display_name).all()


class ExtractionSchemaVersionCRUD(BaseCRUD):
    def __init__(self, db_session: Session):
        super().__init__(ExtractionSchemaVersion, db_session)

    def get_versions_for_doc_type(self, document_type_id: int) -> List[ExtractionSchemaVersion]:
        return self.db_session.query(ExtractionSchemaVersion).filter(
            ExtractionSchemaVersion.document_type_id == document_type_id
        ).order_by(ExtractionSchemaVersion.version.desc()).all()

    def get_active_for_doc_type(self, document_type_id: int) -> Optional[ExtractionSchemaVersion]:
        return self.db_session.query(ExtractionSchemaVersion).filter(
            ExtractionSchemaVersion.document_type_id == document_type_id,
            ExtractionSchemaVersion.is_active == True
        ).first()

    def get_latest_version_number(self, document_type_id: int) -> int:
        result = self.db_session.query(ExtractionSchemaVersion.version).filter(
            ExtractionSchemaVersion.document_type_id == document_type_id
        ).order_by(ExtractionSchemaVersion.version.desc()).first()
        return result[0] if result else 0

    def deactivate_all_for_doc_type(self, document_type_id: int):
        self.db_session.query(ExtractionSchemaVersion).filter(
            ExtractionSchemaVersion.document_type_id == document_type_id
        ).update({"is_active": False})

    def create_version(
        self,
        document_type_id: int,
        notes: Optional[str] = None,
        created_by_id: Optional[int] = None,
        clone_from_version_id: Optional[int] = None
    ) -> ExtractionSchemaVersion:
        next_version = self.get_latest_version_number(document_type_id) + 1
        new_version = ExtractionSchemaVersion(
            document_type_id=document_type_id,
            version=next_version,
            is_active=False,
            notes=notes,
            created_by_id=created_by_id,
        )
        self.db_session.add(new_version)
        self.db_session.flush()

        if clone_from_version_id:
            source_version = self.get_by_id(clone_from_version_id)
            if source_version:
                for field in source_version.fields:
                    new_field = ExtractionSchemaVersionField(
                        schema_version_id=new_version.id,
                        canonical_field_id=field.canonical_field_id,
                        is_required=field.is_required,
                        extraction_priority=field.extraction_priority,
                    )
                    self.db_session.add(new_field)

        return new_version


class ExtractionSchemaVersionFieldCRUD(BaseCRUD):
    def __init__(self, db_session: Session):
        super().__init__(ExtractionSchemaVersionField, db_session)

    def get_fields_for_version(self, schema_version_id: int) -> List[ExtractionSchemaVersionField]:
        return self.db_session.query(ExtractionSchemaVersionField).filter(
            ExtractionSchemaVersionField.schema_version_id == schema_version_id
        ).order_by(ExtractionSchemaVersionField.extraction_priority).all()

    def bulk_set_fields(
        self,
        schema_version_id: int,
        fields: List[dict]
    ):
        self.db_session.query(ExtractionSchemaVersionField).filter(
            ExtractionSchemaVersionField.schema_version_id == schema_version_id
        ).delete()

        for idx, field_data in enumerate(fields):
            new_field = ExtractionSchemaVersionField(
                schema_version_id=schema_version_id,
                canonical_field_id=field_data["canonical_field_id"],
                is_required=field_data.get("is_required", False),
                extraction_priority=field_data.get("extraction_priority", (idx + 1) * 10),
            )
            self.db_session.add(new_field)


class ExtractionPromptTemplateCRUD(BaseCRUD):
    def __init__(self, db_session: Session):
        super().__init__(ExtractionPromptTemplate, db_session)

    def get_templates_for_doc_type(self, document_type_id: int) -> List[ExtractionPromptTemplate]:
        return self.db_session.query(ExtractionPromptTemplate).filter(
            ExtractionPromptTemplate.document_type_id == document_type_id
        ).order_by(ExtractionPromptTemplate.version.desc()).all()

    def get_active_for_doc_type(self, document_type_id: int) -> Optional[ExtractionPromptTemplate]:
        return self.db_session.query(ExtractionPromptTemplate).filter(
            ExtractionPromptTemplate.document_type_id == document_type_id,
            ExtractionPromptTemplate.is_active == True
        ).first()

    def get_latest_version_number(self, document_type_id: int) -> int:
        result = self.db_session.query(ExtractionPromptTemplate.version).filter(
            ExtractionPromptTemplate.document_type_id == document_type_id
        ).order_by(ExtractionPromptTemplate.version.desc()).first()
        return result[0] if result else 0

    def deactivate_all_for_doc_type(self, document_type_id: int):
        self.db_session.query(ExtractionPromptTemplate).filter(
            ExtractionPromptTemplate.document_type_id == document_type_id
        ).update({"is_active": False})

    def create_template(
        self,
        document_type_id: int,
        system_prompt: str,
        extraction_prompt: str,
        model_name: str = "gpt-5.2",
        temperature: float = 0.0,
        max_tokens: int = 8000,
        notes: Optional[str] = None,
        created_by_id: Optional[int] = None,
        clone_from_template_id: Optional[int] = None
    ) -> ExtractionPromptTemplate:
        next_version = self.get_latest_version_number(document_type_id) + 1

        if clone_from_template_id:
            source = self.get_by_id(clone_from_template_id)
            if source:
                system_prompt = system_prompt or source.system_prompt
                extraction_prompt = extraction_prompt or source.extraction_prompt
                model_name = model_name or source.model_name
                temperature = temperature if temperature is not None else source.temperature
                max_tokens = max_tokens or source.max_tokens

        new_template = ExtractionPromptTemplate(
            document_type_id=document_type_id,
            version=next_version,
            is_active=False,
            system_prompt=system_prompt,
            extraction_prompt=extraction_prompt,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            notes=notes,
            created_by_id=created_by_id,
        )
        self.db_session.add(new_template)
        return new_template


class CanonicalFieldCRUD(BaseCRUD):
    def __init__(self, db_session: Session):
        super().__init__(CanonicalField, db_session)

    def get_by_name(self, name: str) -> Optional[CanonicalField]:
        return self.db_session.query(CanonicalField).filter(
            CanonicalField.name == name
        ).first()

    def get_active_fields(self) -> List[CanonicalField]:
        return self.db_session.query(CanonicalField).filter(
            CanonicalField.is_active == True
        ).order_by(CanonicalField.display_name).all()

    def search_fields(self, query: str, limit: int = 50) -> List[CanonicalField]:
        return self.db_session.query(CanonicalField).filter(
            CanonicalField.is_active == True,
            (CanonicalField.name.ilike(f"%{query}%") | CanonicalField.display_name.ilike(f"%{query}%"))
        ).limit(limit).all()
