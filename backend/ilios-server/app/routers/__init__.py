from .account import account_router
from .assets_management import companies_router, device_documents_router, devices_router, sites_router
from .auth import auth_router
from .breadcrumbs import breadcrumbs_router
from .comments import comments_router
from .dashboard import dashboard_notifications_router, dashboard_tasks_router
from .due_diligence import (
    agreements_router,
    chatbot_router,
    co_terminus_router,
    documents_router,
    files_parsing_router,
    files_router,
)
from .finance import (
    finance_actuals_router,
    finance_budgets_router,
    finance_obligations_router,
    finance_portfolio_router,
    finance_vendors_router,
)
from .health import health_router
from .internal import internal_ai_router, internal_router, internal_sites_router
from .investor_dashboard import investor_companies_router
from .operations_and_maintenance import alerts_router, om_companies_router, om_site_cameras_router, om_sites_router
from .reporting import reports_companies_router, reports_router, reports_sites_router
from .security import cameras_router
from .task_tracker import (
    attachments_router,
    board_router,
    board_statuses_router,
    site_visits_router,
    sv_uploads_router,
    tasks_router,
)
from .sales import router as sales_router
from .project_hub import router as project_hub_router
from .workspace import workspace_router
from .admin import access_health_router
from .role_profiles import role_profiles_router
