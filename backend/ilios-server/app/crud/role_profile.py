"""CRUD operations on RoleProfile model."""

from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.crud.base_crud import BaseCRUD
from app.models.role_profile import RoleProfile


class RoleProfileCRUD(BaseCRUD):
    """CRUD operations on RoleProfile model."""

    def __init__(self, db_session: Session):
        super().__init__(model=RoleProfile, db_session=db_session)

    def get_by_key(self, key: str) -> Optional[RoleProfile]:
        """Get a role profile by its key."""
        return self.db_session.query(RoleProfile).filter(RoleProfile.key == key).first()

    def get_active_profiles(self) -> List[RoleProfile]:
        """Get all active role profiles."""
        return (
            self.db_session.query(RoleProfile)
            .filter(RoleProfile.is_active == True)
            .order_by(RoleProfile.display_order, RoleProfile.label)
            .all()
        )

    def get_profiles_for_company_type(self, company_type_key: str) -> List[RoleProfile]:
        """Get role profiles applicable to a specific company type.
        
        Returns profiles where:
        - applicable_company_types is NULL (applies to all)
        - OR applicable_company_types contains the given company_type_key
        """
        return (
            self.db_session.query(RoleProfile)
            .filter(RoleProfile.is_active == True)
            .filter(
                or_(
                    RoleProfile.applicable_company_types.is_(None),
                    RoleProfile.applicable_company_types.contains([company_type_key])
                )
            )
            .order_by(RoleProfile.display_order, RoleProfile.label)
            .all()
        )

    def validate_profile_for_company_type(self, profile_key: str, company_type_key: str) -> bool:
        """Check if a role profile is valid for a given company type."""
        profile = self.get_by_key(profile_key)
        if not profile or not profile.is_active:
            return False
        
        if profile.applicable_company_types is None:
            return True
        
        return company_type_key in profile.applicable_company_types

    def delete_by_key(self, key: str) -> bool:
        """Delete a role profile by its key. Returns True if deleted, False if not found."""
        profile = self.get_by_key(key)
        if profile:
            self.db_session.delete(profile)
            self.db_session.commit()
            return True
        return False
