"""Admin Extraction Registry Router

Provides endpoints for managing the extraction registry:
- Document types
- Schema versions
- Prompt templates
- Canonical fields

All endpoints are role-gated to System User or Company Admin Full.
"""

import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.schema.user import CurrentUserSchema
from app.crud.extraction_registry import (
    ExtractionDocumentTypeCRUD,
    ExtractionSchemaVersionCRUD,
    ExtractionSchemaVersionFieldCRUD,
    ExtractionPromptTemplateCRUD,
    CanonicalFieldCRUD,
)
from app.models.extraction_registry import (
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_EXTRACTION_PROMPT,
)

logger = logging.getLogger(__name__)
extraction_registry_router = APIRouter()


def require_admin_access(current_user: CurrentUserSchema, db_session: Session):
    if current_user.role not in ["System User", "Company Admin Full", "Admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for extraction registry management"
        )


class CanonicalFieldSchema(BaseModel):
    id: int
    name: str
    display_name: str
    field_type: str
    validation_regex: Optional[str] = None
    description: Optional[str] = None
    is_active: bool


class CanonicalFieldCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    field_type: str = Field(default="text", max_length=50)
    validation_regex: Optional[str] = None
    description: Optional[str] = None


class CanonicalFieldUpdateSchema(BaseModel):
    display_name: Optional[str] = None
    field_type: Optional[str] = None
    validation_regex: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class DocumentTypeSchema(BaseModel):
    id: int
    name: str
    display_name: str
    category: str
    is_parsable: bool
    is_active: bool


class DocumentTypeCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(default="other", max_length=50)
    is_parsable: bool = True


class DocumentTypeUpdateSchema(BaseModel):
    display_name: Optional[str] = None
    category: Optional[str] = None
    is_parsable: Optional[bool] = None
    is_active: Optional[bool] = None


class SchemaVersionFieldSchema(BaseModel):
    canonical_field_id: int
    field_name: str
    field_display_name: str
    field_type: str
    is_required: bool
    extraction_priority: int


class SchemaVersionSchema(BaseModel):
    id: int
    document_type_id: int
    version: int
    is_active: bool
    notes: Optional[str] = None
    created_at: str
    fields: List[SchemaVersionFieldSchema] = []


class SchemaVersionCreateSchema(BaseModel):
    notes: Optional[str] = None
    clone_from_version_id: Optional[int] = None


class SchemaVersionFieldsUpdateSchema(BaseModel):
    fields: List[dict]


class PromptTemplateSchema(BaseModel):
    id: int
    document_type_id: int
    version: int
    is_active: bool
    system_prompt: Optional[str] = None
    extraction_prompt: str
    model_name: str
    temperature: float
    max_tokens: int
    notes: Optional[str] = None
    created_at: str


class PromptTemplateCreateSchema(BaseModel):
    system_prompt: Optional[str] = None
    extraction_prompt: Optional[str] = None
    model_name: str = "gpt-5.2"
    temperature: float = 0.0
    max_tokens: int = 8000
    notes: Optional[str] = None
    clone_from_template_id: Optional[int] = None


class PromptTemplateUpdateSchema(BaseModel):
    system_prompt: Optional[str] = None
    extraction_prompt: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    notes: Optional[str] = None


@extraction_registry_router.get("/canonical-fields", response_model=List[CanonicalFieldSchema])
async def list_canonical_fields(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
    active_only: bool = True,
    search: Optional[str] = None,
):
    require_admin_access(current_user, db_session)
    crud = CanonicalFieldCRUD(db_session)
    if search:
        fields = crud.search_fields(search)
    elif active_only:
        fields = crud.get_active_fields()
    else:
        fields = crud.get_all()
    return [CanonicalFieldSchema(
        id=f.id,
        name=f.name,
        display_name=f.display_name,
        field_type=f.field_type,
        validation_regex=f.validation_regex,
        description=f.description,
        is_active=f.is_active,
    ) for f in fields]


@extraction_registry_router.post("/canonical-fields", response_model=CanonicalFieldSchema, status_code=status.HTTP_201_CREATED)
async def create_canonical_field(
    data: CanonicalFieldCreateSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_admin_access(current_user, db_session)
    crud = CanonicalFieldCRUD(db_session)
    if crud.get_by_name(data.name):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Field with name '{data.name}' already exists")
    field = crud.create_item({
        "name": data.name,
        "display_name": data.display_name,
        "field_type": data.field_type,
        "validation_regex": data.validation_regex,
        "description": data.description,
        "is_active": True,
    })
    db_session.commit()
    return CanonicalFieldSchema(
        id=field.id,
        name=field.name,
        display_name=field.display_name,
        field_type=field.field_type,
        validation_regex=field.validation_regex,
        description=field.description,
        is_active=field.is_active,
    )


@extraction_registry_router.patch("/canonical-fields/{field_id}", response_model=CanonicalFieldSchema)
async def update_canonical_field(
    field_id: int,
    data: CanonicalFieldUpdateSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_admin_access(current_user, db_session)
    crud = CanonicalFieldCRUD(db_session)
    field = crud.get_by_id(field_id)
    if not field:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Field not found")
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        crud.update_by_id(field_id, update_data)
        db_session.commit()
        db_session.refresh(field)
    return CanonicalFieldSchema(
        id=field.id,
        name=field.name,
        display_name=field.display_name,
        field_type=field.field_type,
        validation_regex=field.validation_regex,
        description=field.description,
        is_active=field.is_active,
    )


@extraction_registry_router.get("/document-types", response_model=List[DocumentTypeSchema])
async def list_document_types(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
    active_only: bool = True,
):
    require_admin_access(current_user, db_session)
    crud = ExtractionDocumentTypeCRUD(db_session)
    types = crud.get_active_types() if active_only else crud.get_all()
    return [DocumentTypeSchema(
        id=t.id,
        name=t.name,
        display_name=t.display_name,
        category=t.category,
        is_parsable=t.is_parsable,
        is_active=t.is_active,
    ) for t in types]


@extraction_registry_router.post("/document-types", response_model=DocumentTypeSchema, status_code=status.HTTP_201_CREATED)
async def create_document_type(
    data: DocumentTypeCreateSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_admin_access(current_user, db_session)
    crud = ExtractionDocumentTypeCRUD(db_session)
    if crud.get_by_name(data.name):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Document type '{data.name}' already exists")
    doc_type = crud.create_item({
        "name": data.name,
        "display_name": data.display_name,
        "category": data.category,
        "is_parsable": data.is_parsable,
        "is_active": True,
    })

    schema_crud = ExtractionSchemaVersionCRUD(db_session)
    schema_v1 = schema_crud.create_version(doc_type.id, notes="Initial version", created_by_id=current_user.id)
    schema_v1.is_active = True

    prompt_crud = ExtractionPromptTemplateCRUD(db_session)
    prompt_v1 = prompt_crud.create_template(
        document_type_id=doc_type.id,
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        extraction_prompt=DEFAULT_EXTRACTION_PROMPT,
        created_by_id=current_user.id,
        notes="Initial version",
    )
    prompt_v1.is_active = True

    db_session.commit()
    return DocumentTypeSchema(
        id=doc_type.id,
        name=doc_type.name,
        display_name=doc_type.display_name,
        category=doc_type.category,
        is_parsable=doc_type.is_parsable,
        is_active=doc_type.is_active,
    )


@extraction_registry_router.patch("/document-types/{doc_type_id}", response_model=DocumentTypeSchema)
async def update_document_type(
    doc_type_id: int,
    data: DocumentTypeUpdateSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_admin_access(current_user, db_session)
    crud = ExtractionDocumentTypeCRUD(db_session)
    doc_type = crud.get_by_id(doc_type_id)
    if not doc_type:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document type not found")
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        crud.update_by_id(doc_type_id, update_data)
        db_session.commit()
        db_session.refresh(doc_type)
    return DocumentTypeSchema(
        id=doc_type.id,
        name=doc_type.name,
        display_name=doc_type.display_name,
        category=doc_type.category,
        is_parsable=doc_type.is_parsable,
        is_active=doc_type.is_active,
    )


@extraction_registry_router.get("/document-types/{doc_type_id}/schema-versions", response_model=List[SchemaVersionSchema])
async def list_schema_versions(
    doc_type_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_admin_access(current_user, db_session)
    crud = ExtractionSchemaVersionCRUD(db_session)
    versions = crud.get_versions_for_doc_type(doc_type_id)
    result = []
    for v in versions:
        fields = []
        for f in v.get_ordered_fields():
            cf = f.canonical_field
            fields.append(SchemaVersionFieldSchema(
                canonical_field_id=cf.id,
                field_name=cf.name,
                field_display_name=cf.display_name,
                field_type=cf.field_type,
                is_required=f.is_required,
                extraction_priority=f.extraction_priority,
            ))
        result.append(SchemaVersionSchema(
            id=v.id,
            document_type_id=v.document_type_id,
            version=v.version,
            is_active=v.is_active,
            notes=v.notes,
            created_at=v.created_at.isoformat() if v.created_at else None,
            fields=fields,
        ))
    return result


@extraction_registry_router.post("/document-types/{doc_type_id}/schema-versions", response_model=SchemaVersionSchema, status_code=status.HTTP_201_CREATED)
async def create_schema_version(
    doc_type_id: int,
    data: SchemaVersionCreateSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_admin_access(current_user, db_session)
    doc_type_crud = ExtractionDocumentTypeCRUD(db_session)
    if not doc_type_crud.get_by_id(doc_type_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document type not found")

    crud = ExtractionSchemaVersionCRUD(db_session)
    clone_id = data.clone_from_version_id
    if not clone_id:
        active = crud.get_active_for_doc_type(doc_type_id)
        clone_id = active.id if active else None

    version = crud.create_version(
        document_type_id=doc_type_id,
        notes=data.notes,
        created_by_id=current_user.id,
        clone_from_version_id=clone_id,
    )
    db_session.commit()
    db_session.refresh(version)

    fields = []
    for f in version.get_ordered_fields():
        cf = f.canonical_field
        fields.append(SchemaVersionFieldSchema(
            canonical_field_id=cf.id,
            field_name=cf.name,
            field_display_name=cf.display_name,
            field_type=cf.field_type,
            is_required=f.is_required,
            extraction_priority=f.extraction_priority,
        ))
    return SchemaVersionSchema(
        id=version.id,
        document_type_id=version.document_type_id,
        version=version.version,
        is_active=version.is_active,
        notes=version.notes,
        created_at=version.created_at.isoformat() if version.created_at else None,
        fields=fields,
    )


@extraction_registry_router.post("/schema-versions/{version_id}/activate")
async def activate_schema_version(
    version_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_admin_access(current_user, db_session)
    crud = ExtractionSchemaVersionCRUD(db_session)
    version = crud.get_by_id(version_id)
    if not version:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Schema version not found")

    crud.deactivate_all_for_doc_type(version.document_type_id)
    version.is_active = True
    db_session.commit()
    return {"activated": True, "version_id": version_id}


@extraction_registry_router.post("/schema-versions/{version_id}/fields")
async def set_schema_version_fields(
    version_id: int,
    data: SchemaVersionFieldsUpdateSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_admin_access(current_user, db_session)
    version_crud = ExtractionSchemaVersionCRUD(db_session)
    version = version_crud.get_by_id(version_id)
    if not version:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Schema version not found")

    field_crud = ExtractionSchemaVersionFieldCRUD(db_session)
    field_crud.bulk_set_fields(version_id, data.fields)
    db_session.commit()
    return {"updated": True, "version_id": version_id, "field_count": len(data.fields)}


@extraction_registry_router.get("/document-types/{doc_type_id}/prompt-templates", response_model=List[PromptTemplateSchema])
async def list_prompt_templates(
    doc_type_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_admin_access(current_user, db_session)
    crud = ExtractionPromptTemplateCRUD(db_session)
    templates = crud.get_templates_for_doc_type(doc_type_id)
    return [PromptTemplateSchema(
        id=t.id,
        document_type_id=t.document_type_id,
        version=t.version,
        is_active=t.is_active,
        system_prompt=t.system_prompt,
        extraction_prompt=t.extraction_prompt,
        model_name=t.model_name,
        temperature=t.temperature,
        max_tokens=t.max_tokens,
        notes=t.notes,
        created_at=t.created_at.isoformat() if t.created_at else None,
    ) for t in templates]


@extraction_registry_router.post("/document-types/{doc_type_id}/prompt-templates", response_model=PromptTemplateSchema, status_code=status.HTTP_201_CREATED)
async def create_prompt_template(
    doc_type_id: int,
    data: PromptTemplateCreateSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_admin_access(current_user, db_session)
    doc_type_crud = ExtractionDocumentTypeCRUD(db_session)
    if not doc_type_crud.get_by_id(doc_type_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document type not found")

    crud = ExtractionPromptTemplateCRUD(db_session)
    clone_id = data.clone_from_template_id
    if not clone_id:
        active = crud.get_active_for_doc_type(doc_type_id)
        clone_id = active.id if active else None

    template = crud.create_template(
        document_type_id=doc_type_id,
        system_prompt=data.system_prompt or DEFAULT_SYSTEM_PROMPT,
        extraction_prompt=data.extraction_prompt or DEFAULT_EXTRACTION_PROMPT,
        model_name=data.model_name,
        temperature=data.temperature,
        max_tokens=data.max_tokens,
        notes=data.notes,
        created_by_id=current_user.id,
        clone_from_template_id=clone_id,
    )
    db_session.commit()
    db_session.refresh(template)
    return PromptTemplateSchema(
        id=template.id,
        document_type_id=template.document_type_id,
        version=template.version,
        is_active=template.is_active,
        system_prompt=template.system_prompt,
        extraction_prompt=template.extraction_prompt,
        model_name=template.model_name,
        temperature=template.temperature,
        max_tokens=template.max_tokens,
        notes=template.notes,
        created_at=template.created_at.isoformat() if template.created_at else None,
    )


@extraction_registry_router.post("/prompt-templates/{template_id}/activate")
async def activate_prompt_template(
    template_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_admin_access(current_user, db_session)
    crud = ExtractionPromptTemplateCRUD(db_session)
    template = crud.get_by_id(template_id)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prompt template not found")

    crud.deactivate_all_for_doc_type(template.document_type_id)
    template.is_active = True
    db_session.commit()
    return {"activated": True, "template_id": template_id}


@extraction_registry_router.patch("/prompt-templates/{template_id}", response_model=PromptTemplateSchema)
async def update_prompt_template(
    template_id: int,
    data: PromptTemplateUpdateSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_admin_access(current_user, db_session)
    crud = ExtractionPromptTemplateCRUD(db_session)
    template = crud.get_by_id(template_id)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prompt template not found")
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        crud.update_by_id(template_id, update_data)
        db_session.commit()
        db_session.refresh(template)
    return PromptTemplateSchema(
        id=template.id,
        document_type_id=template.document_type_id,
        version=template.version,
        is_active=template.is_active,
        system_prompt=template.system_prompt,
        extraction_prompt=template.extraction_prompt,
        model_name=template.model_name,
        temperature=template.temperature,
        max_tokens=template.max_tokens,
        notes=template.notes,
        created_at=template.created_at.isoformat() if template.created_at else None,
    )
