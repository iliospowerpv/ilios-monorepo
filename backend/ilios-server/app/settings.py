import logging
from typing import Optional

from pydantic import EmailStr, PostgresDsn, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.static.settings_defaults import DEFAULT_LOG_LEVEL

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    # framework related settings
    app_title: str = "Ilios APIs"
    app_description: str = "The APIs for the Ilios application MVP"

    # app related settings
    secret_key: str
    api_key: str
    access_token_expire_minutes: Optional[int] = 60 * 24
    # Global Admin safeguards (Phase 1)
    # Hard cap on the number of users with is_global_admin=True. Grants
    # are refused once this limit is reached. Bounds blast radius of the
    # privilege.
    max_global_admins: Optional[int] = 3
    # Shorter access-token (and DB session) lifetime for global admin
    # sessions, to limit damage from a stolen token.
    global_admin_session_minutes: Optional[int] = 15
    invitation_link_expire_days: Optional[int] = 1
    invitation_url: str
    reset_password_expires_minutes: Optional[int] = 30
    password_reset_url: str
    permissions_template_path: Optional[str] = (
        "app/static/permissions_template.json"  # path to the .json file with default permissions
    )
    support_email: Optional[EmailStr]
    login_url: Optional[str]

    # pre-defined admin user
    system_user_first_name: Optional[str] = "System"
    system_user_last_name: Optional[str] = "User"
    system_user_email: Optional[EmailStr] = "system@user.com"
    system_user_phone: Optional[str] = "0123456789"
    system_user_password: str

    # logging middleware settings
    log_level: Optional[str] = DEFAULT_LOG_LEVEL
    enable_requests_logger: Optional[bool] = True
    requests_logger_max_response: Optional[int] = None
    requests_logger_include_headers: Optional[bool] = False
    # audit middleware settings
    enable_audit_logger: Optional[bool] = True

    # email sending settings
    mailgun_rest_api_endpoint: str
    mailgun_api_key: str
    mailgun_domain_name: str
    default_email_sender: str

    # DB settings - supports both custom db_* vars and Replit's PG* vars
    db_host: Optional[str] = None
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_name: Optional[str] = None
    db_dsn: Optional[str] = None
    
    # Replit PostgreSQL environment variables (auto-populated)
    PGHOST: Optional[str] = None
    PGUSER: Optional[str] = None
    PGPASSWORD: Optional[str] = None
    PGDATABASE: Optional[str] = None
    PGPORT: Optional[str] = None
    DATABASE_URL: Optional[str] = None

    # Storage settings
    storage_provider: str = "replit"  # "replit" (default) or "gcs"
    replit_storage_prefix: str = "ilios"  # Prefix for Replit Object Storage keys
    
    # Google Cloud Storage settings (OPTIONAL - only required if storage_provider="gcs")
    due_diligence_gcs_bucket: Optional[str] = None
    task_attachments_gcs_bucket: Optional[str] = None
    device_documents_gcs_bucket: Optional[str] = None
    sv_uploads_gcs_bucket: Optional[str] = None
    service_account_key_file_path: Optional[str] = None
    
    # File upload settings
    allowed_extensions: Optional[str] = "pdf,docx,jpeg,jpg,png"
    ai_parsing_allowed_extensions: Optional[str] = "pdf,docx"
    sa_uploads_allowed_extensions: Optional[str] = "jpeg,jpg,png"
    allowed_filesize: Optional[int] = 100 * 1024 * 1024  # Max file size in bytes. Default 100 MB.
    file_download_link_expiration_minutes: Optional[int] = 60 * 2  # 2 hours

    # AI integration settings
    file_parse_function_url: str
    co_terminus_function_url: str
    co_terminus_stuck_threshold: Optional[int] = 900  # 15 min
    chatbot_upload_file_function_url: str
    chatbot_mark_actual_function_url: str
    chatbot_delete_file_function_url: str
    chatbot_session_token_function_url: str
    ml_api_key: str

    # Telemetry integration settings
    telemetry_token_function_url: str
    telemetry_sites_function_url: str
    telemetry_devices_function_url: str
    telemetry_device_static_info_func_url: str

    # Google Secrets settings
    gcp_project_id: int

    # AI parsing config
    ai_parsing_config_path: Optional[str] = "configs/ai_parsing_config.json"
    allow_config_fallback: bool = False  # Set True only for migration period; registry is authoritative
    agreement_names_mapping_config_path: Optional[str] = "configs/agreement_names_mapping_config.json"
    co_terminus_config_path: Optional[str] = "configs/co_terminus_config.json"

    # Parsing guardrails and resource limits
    parsing_min_text_chars: int = 500  # Min extracted chars; below this suggests scanned/image PDF
    parsing_max_file_size_mb: int = 25  # Max file size in MB before rejection
    parsing_max_pdf_pages: int = 200  # Max PDF pages before rejection
    parsing_max_chars_to_llm: int = 200000  # Max chars sent to LLM; truncates beyond this

    # Rombus settings
    rombus_api_key: str

    # Telemetry settings
    firestore_db_name: Optional[str] = "(default)"
    telemetry_project_name: Optional[str] = "prj-ilios-telemetry"
    telemetry_config_collection_name: Optional[str] = "telemetry-config"
    environment_name: str

    # BigQuery settings
    telemetry_bq_project_id: Optional[str] = "prj-ilios-telemetry"
    telemetry_bq_job_id_prefix: Optional[str] = "platform-query-job-"
    # tables for characteristics sync, the same for all the envs
    bq_device_characteristics_table: Optional[str] = "device_characteristics"
    bq_site_characteristics_table: Optional[str] = "site_characteristics"

    # Redis cache settings - supports REDIS_URL or REDIS_CONNECTION_URL
    REDIS_URL: Optional[str] = None
    REDIS_CONNECTION_URL: Optional[str] = None
    
    @property
    def redis_connection_string(self) -> str:
        """Get Redis URL from environment variables.
        Priority: REDIS_URL > REDIS_CONNECTION_URL
        Supports both redis:// (no TLS) and rediss:// (TLS) schemes.
        """
        return self.REDIS_URL or self.REDIS_CONNECTION_URL or ""
    # TODO rename it based on the value, for example, cache_15_minutes and cache_8_hours
    site_dashboard_expiration_seconds: Optional[int] = 15 * 60  # 15 minutes for dashboard cache
    site_7_days_performance_expiration_seconds: Optional[int] = 8 * 60 * 60  # 8 hours for past 7 days performance
    # originally, PowerBI access token expires in 3599s after the generation (almost an hour), thus the value a bit lower
    pbi_access_token_expiration_seconds: Optional[int] = 3500
    # by default, Embed token expiration set to 15min, this set a bit lover value (10min)
    pbi_embed_token_expiration_seconds: Optional[int] = 10 * 60

    # PowerBI settings
    pbi_tenant_id: str
    pbi_client_id: str
    pbi_client_secret: str
    pbi_workspace_id: str

    # Other configurables
    device_no_respond_threshold: Optional[int] = 30 * 60  # 30 minutes as default

    @field_validator("db_dsn", mode="after")
    @classmethod
    def assemble_db_uri(cls, field_value, info: ValidationInfo) -> str:
        if isinstance(field_value, str) and field_value:
            return field_value

        # Highest priority: explicit DATABASE_URL (used by Replit Helium Postgres in deployments).
        # Normalize the scheme so SQLAlchemy uses the psycopg2 driver consistently.
        import os as _os
        database_url = info.data.get("DATABASE_URL") or _os.environ.get("DATABASE_URL")
        if database_url:
            if database_url.startswith("postgres://"):
                database_url = "postgresql+psycopg2://" + database_url[len("postgres://"):]
            elif database_url.startswith("postgresql://"):
                database_url = "postgresql+psycopg2://" + database_url[len("postgresql://"):]
            return database_url

        # Fallback: build from db_* vars or Replit's PG* vars.
        # Read from the model fields first, then env directly as a last resort.
        def _v(field_name, env_name):
            return info.data.get(field_name) or info.data.get(env_name) or _os.environ.get(env_name)

        db_user = _v("db_user", "PGUSER")
        db_password = _v("db_password", "PGPASSWORD")
        db_host = _v("db_host", "PGHOST")
        db_name = _v("db_name", "PGDATABASE")
        pg_port = info.data.get("PGPORT") or _os.environ.get("PGPORT")

        if not db_host:
            raise ValueError(
                "Database is not configured: set DATABASE_URL, or db_host/db_user/db_password/db_name, "
                "or PGHOST/PGUSER/PGPASSWORD/PGDATABASE."
            )

        # Build connection string with port if available
        host_with_port = f"{db_host}:{pg_port}" if pg_port and not info.data.get("db_host") else db_host

        return PostgresDsn.build(
            scheme="postgresql+psycopg2",
            username=db_user,
            password=db_password,
            host=host_with_port,
            path=db_name or "",
        ).unicode_string()

    @field_validator("allowed_extensions")
    @classmethod
    def parse_allowed_extensions_to_tuple(cls, allowed_extensions) -> tuple:
        return allowed_extensions.split(",")

    @field_validator("sa_uploads_allowed_extensions")
    @classmethod
    def parse_sa_uploads_allowed_extensions_to_tuple(cls, sa_uploads_allowed_extensions) -> tuple:
        return sa_uploads_allowed_extensions.split(",")

    @field_validator("log_level")
    @classmethod
    def set_minimum_log_level(cls, log_level) -> str:
        # uppercase log level to follow logging levels naming convention
        log_level = log_level.upper()
        # validate if input log level is valid, otherwise set it to default
        if log_level not in list(logging.getLevelNamesMapping()):
            logger.warning(f"Log level <{log_level}> not supported, setting <{DEFAULT_LOG_LEVEL}> as default")
            log_level = DEFAULT_LOG_LEVEL
        return log_level


try:
    settings = Settings()
except Exception as _e:
    import sys, traceback
    sys.stderr.write("\n========== SETTINGS INIT FAILED ==========\n")
    sys.stderr.write(f"{type(_e).__name__}: {_e}\n")
    sys.stderr.write(traceback.format_exc())
    sys.stderr.write("==========================================\n")
    sys.stderr.flush()
    raise
