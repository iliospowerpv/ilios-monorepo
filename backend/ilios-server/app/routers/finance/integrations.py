"""Finance integration configuration endpoints.

Company-level endpoints for configuring external finance system integrations.
All endpoints require company_admin role - fail closed on permission denial.

NOTE: This is a READ-ONLY integration. No write-back to external systems.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.permission_guards import require_module_permission
from app.schema.user import CurrentUserSchema
from app.static.permissions import PermissionsModules
from app.crud.finance_integration import FinanceIntegrationCRUD
from app.crud.company import CompanyCRUD
from app.models.finance_integration import FinanceIntegrationStatus
from app.schema.finance_integration import (
    FinanceIntegrationCreate,
    FinanceIntegrationUpdate,
    FinanceIntegrationResponse,
    FinanceIntegrationsListResponse,
    FinanceIntegrationTestResponse,
    FinanceProviderInfo,
)
from app.services.finance import get_provider_registry, FinanceProviderError
from app.schema.finance_data import FinanceSyncTriggerResponse
from app.services.finance.sync_service import FinanceSyncService


router = APIRouter(prefix="/finance/integrations", tags=["finance-integrations"])


def _require_company_admin_with_finance_permission(
    db: Session,
    current_user: CurrentUserSchema,
    company_id: int,
) -> None:
    """Verify the user is a company admin with Finance module permission.
    
    Per the roles contract, configuring finance integrations requires:
    1. company_admin role
    2. Finance module edit permission
    
    Uses require_module_permission for standardized 403 error payloads.
    
    Args:
        db: Database session.
        current_user: The current authenticated user.
        company_id: The company ID to check access for.
        
    Raises:
        HTTPException: 403 if user is not a company admin or lacks Finance permission.
    """
    if current_user.has_platform_bypass:
        return
    
    access = require_module_permission(
        user_id=current_user.id,
        company_id=company_id,
        db_session=db,
        module_key=PermissionsModules.finance.value,
        action="edit",
    )
    
    if access.effective_base_role != "company_admin":
        from app.schema.authorization_error import create_authorization_error
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=create_authorization_error(
                reason_code="insufficient_role",
                module_key=PermissionsModules.finance.value,
                action="edit",
                grant_sources=access.grant_sources,
                company_id=company_id,
            )
        )


def _integration_to_response(
    integration,
    provider_display_name: str = None,
) -> FinanceIntegrationResponse:
    """Convert integration model to response schema."""
    registry = get_provider_registry()
    
    if not provider_display_name:
        provider_class = registry.get_provider_class(integration.provider_key)
        if provider_class:
            instance = provider_class(credentials={})
            provider_display_name = instance.display_name
        else:
            provider_display_name = integration.provider_key.title()
    
    return FinanceIntegrationResponse(
        id=integration.id,
        company_id=integration.company_id,
        provider_key=integration.provider_key,
        provider_display_name=provider_display_name,
        config=integration.config_json,
        status=FinanceIntegrationStatus(integration.status.value),
        last_tested_at=integration.last_tested_at,
        last_test_success=integration.last_test_success,
        last_error=integration.last_error,
        created_at=integration.created_at,
        updated_at=integration.updated_at,
    )


@router.get(
    "/{company_id}",
    response_model=FinanceIntegrationsListResponse,
    summary="Get finance integrations for a company",
    description="Get all configured finance integrations for a company and list of available providers.",
)
def get_company_integrations(
    company_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db: Session = Depends(get_session),
) -> FinanceIntegrationsListResponse:
    """Get all finance integrations and available providers for a company."""
    _require_company_admin_with_finance_permission(db, current_user, company_id)
    
    company = CompanyCRUD(db).get_by_id(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    crud = FinanceIntegrationCRUD(db)
    integrations = crud.get_by_company(company_id)
    
    registry = get_provider_registry()
    available_providers = [
        FinanceProviderInfo(
            key=p["key"],
            display_name=p["display_name"],
            supports_budgets=p["supports_budgets"],
        )
        for p in registry.list_providers()
    ]
    
    return FinanceIntegrationsListResponse(
        integrations=[_integration_to_response(i) for i in integrations],
        available_providers=available_providers,
    )


@router.post(
    "/{company_id}",
    response_model=FinanceIntegrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a finance integration",
    description="Configure a new finance integration for a company.",
)
def create_integration(
    company_id: int,
    payload: FinanceIntegrationCreate,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db: Session = Depends(get_session),
) -> FinanceIntegrationResponse:
    """Create a new finance integration for a company."""
    _require_company_admin_with_finance_permission(db, current_user, company_id)
    
    company = CompanyCRUD(db).get_by_id(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    registry = get_provider_registry()
    if not registry.get_provider_class(payload.provider_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_provider",
                "provider_key": payload.provider_key,
                "available_providers": [p["key"] for p in registry.list_providers()],
            }
        )
    
    crud = FinanceIntegrationCRUD(db)
    
    existing = crud.get_by_company_and_provider(company_id, payload.provider_key)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "integration_exists",
                "message": f"An integration for {payload.provider_key} already exists for this company",
            }
        )
    
    credentials = {}
    if payload.credentials:
        if payload.credentials.api_key:
            credentials["api_key"] = payload.credentials.api_key
        if payload.credentials.api_secret:
            credentials["api_secret"] = payload.credentials.api_secret
        if payload.credentials.base_url:
            credentials["base_url"] = payload.credentials.base_url
        if payload.credentials.additional:
            credentials.update(payload.credentials.additional)
    
    integration = crud.create_integration(
        company_id=company_id,
        provider_key=payload.provider_key,
        credentials=credentials,
        config=payload.config,
        created_by_user_id=current_user.id,
    )
    
    return _integration_to_response(integration)


@router.patch(
    "/{company_id}/{provider_key}",
    response_model=FinanceIntegrationResponse,
    summary="Update a finance integration",
    description="Update an existing finance integration configuration.",
)
def update_integration(
    company_id: int,
    provider_key: str,
    payload: FinanceIntegrationUpdate,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db: Session = Depends(get_session),
) -> FinanceIntegrationResponse:
    """Update an existing finance integration."""
    _require_company_admin_with_finance_permission(db, current_user, company_id)
    
    crud = FinanceIntegrationCRUD(db)
    integration = crud.get_by_company_and_provider(company_id, provider_key)
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    credentials = None
    if payload.credentials:
        credentials = {}
        if payload.credentials.api_key:
            credentials["api_key"] = payload.credentials.api_key
        if payload.credentials.api_secret:
            credentials["api_secret"] = payload.credentials.api_secret
        if payload.credentials.base_url:
            credentials["base_url"] = payload.credentials.base_url
        if payload.credentials.additional:
            credentials.update(payload.credentials.additional)
    
    updated = crud.update_integration(
        integration_id=integration.id,
        credentials=credentials,
        config=payload.config,
        status=payload.status,
        updated_by_user_id=current_user.id,
    )
    
    return _integration_to_response(updated)


@router.post(
    "/{company_id}/{provider_key}/test",
    response_model=FinanceIntegrationTestResponse,
    summary="Test a finance integration connection",
    description="Test the connection to the external finance system.",
)
def test_integration(
    company_id: int,
    provider_key: str,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db: Session = Depends(get_session),
) -> FinanceIntegrationTestResponse:
    """Test the connection for a finance integration."""
    _require_company_admin_with_finance_permission(db, current_user, company_id)
    
    crud = FinanceIntegrationCRUD(db)
    integration = crud.get_by_company_and_provider(company_id, provider_key)
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    credentials = crud.get_decrypted_credentials(integration.id)
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No credentials configured for this integration"
        )
    
    registry = get_provider_registry()
    
    try:
        provider = registry.create_provider(
            provider_key=provider_key,
            credentials=credentials,
            config=integration.config_json,
        )
        
        result = provider.test_connection()
        
        crud.update_test_result(
            integration_id=integration.id,
            success=result.success,
            error_message=result.message if not result.success else None,
        )
        
        return FinanceIntegrationTestResponse(
            success=result.success,
            status=result.status.value,
            message=result.message,
            tested_at=result.tested_at,
            details=result.details,
        )
        
    except FinanceProviderError as e:
        crud.update_test_result(
            integration_id=integration.id,
            success=False,
            error_message=str(e),
        )
        
        return FinanceIntegrationTestResponse(
            success=False,
            status="error",
            message=str(e),
            tested_at=datetime.utcnow(),
            details={"error_code": e.error_code},
        )


@router.delete(
    "/{company_id}/{provider_key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a finance integration",
    description="Remove a finance integration configuration.",
)
def delete_integration(
    company_id: int,
    provider_key: str,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db: Session = Depends(get_session),
):
    """Delete a finance integration."""
    _require_company_admin_with_finance_permission(db, current_user, company_id)
    
    crud = FinanceIntegrationCRUD(db)
    integration = crud.get_by_company_and_provider(company_id, provider_key)
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    crud.delete_integration(integration.id)


@router.post(
    "/{company_id}/{provider_key}/sync",
    response_model=FinanceSyncTriggerResponse,
    summary="Trigger a finance data sync",
    description="Requires company_admin + finance:edit. Ingests accounts and transactions from the provider.",
)
def trigger_sync(
    company_id: int,
    provider_key: str,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db: Session = Depends(get_session),
) -> FinanceSyncTriggerResponse:
    """Trigger a data sync for a finance integration."""
    _require_company_admin_with_finance_permission(db, current_user, company_id)

    company = CompanyCRUD(db).get_by_id(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    crud = FinanceIntegrationCRUD(db)
    integration = crud.get_by_company_and_provider(company_id, provider_key)
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No integration configured for provider '{provider_key}'",
        )

    service = FinanceSyncService(db)
    run = service.execute_sync(
        company_id=company_id,
        provider_key=provider_key,
        triggered_by_user_id=current_user.id,
    )

    run_status = run.status.value if hasattr(run.status, "value") else str(run.status)
    message = (
        "Sync completed successfully"
        if run_status == "succeeded"
        else f"Sync failed: {run.last_error}"
    )

    return FinanceSyncTriggerResponse(
        sync_run_id=run.id,
        correlation_id=run.correlation_id,
        status=run_status,
        message=message,
    )
