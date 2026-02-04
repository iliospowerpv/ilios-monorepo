import re
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.base_crud import BaseCRUD
from app.models.project_facts import CanonicalField


class CanonicalFieldCRUD(BaseCRUD):
    def __init__(self, db_session: Session):
        super().__init__(CanonicalField, db_session)

    def get_by_name(self, name: str) -> Optional[CanonicalField]:
        return self.db_session.query(CanonicalField).filter(CanonicalField.name == name).first()

    def get_by_display_name(self, display_name: str) -> Optional[CanonicalField]:
        return self.db_session.query(CanonicalField).filter(
            CanonicalField.display_name == display_name
        ).first()

    def get_all_active(self) -> list[CanonicalField]:
        return self.db_session.query(CanonicalField).filter(
            CanonicalField.is_active == True
        ).all()

    def get_or_create(self, name: str, display_name: str, field_type: str = "text") -> CanonicalField:
        existing = self.get_by_name(name)
        if existing:
            return existing
        return self.create_item({
            "name": name,
            "display_name": display_name,
            "field_type": field_type,
        })

    @staticmethod
    def normalize_key_name(display_name: str) -> str:
        normalized = display_name.lower()
        normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
        normalized = re.sub(r'\s+', '_', normalized.strip())
        return normalized

    def find_by_extraction_key(self, extraction_key: str) -> Optional[CanonicalField]:
        normalized = self.normalize_key_name(extraction_key)
        field = self.get_by_name(normalized)
        if field:
            return field
        return self.get_by_display_name(extraction_key)
