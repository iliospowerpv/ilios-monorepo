import enum


class BaseMessageEnum(enum.Enum):
    def __str__(self):
        return self.value


class UserAccountMessages(BaseMessageEnum):
    account_not_exists = "We can’t find account with such email"
    account_not_setup = "Account is not fully set up"


class CompanyMessages(BaseMessageEnum):
    company_already_exists = "This name already exists. Please try another name"


class RoleMessages(BaseMessageEnum):
    role_create_success = "Role has been created"
    role_update_success = "Role has been updated"


class UserMessages(BaseMessageEnum):
    email_already_taken = "Another user with such email already exists"
    sites_not_found = "Some of requested sites not found: {}"


class AccountMessages(BaseMessageEnum):
    link_deactivated = "The link is deactivated, please, contact the admin"
    link_expired = "The link has expired, please, contact the admin"


class DeviceMessages(BaseMessageEnum):
    device_update_success = "Device has been successfully updated"
    device_not_found = "Device with such id is not found"
    archived_device_update_error = "Update of devices in statuses 'Decommissioned' or 'Deleted on DAS' is prohibited"
    device_deleted_on_das_success = "Device has been marked as 'Deleted on Das'"
    device_not_connected_to_das = "DAS connections is not responding - Failed to fetch data"
    no_telemetry_data_received = "No data is available from the DAS system"
    device_telemetry_info_update_success = "Data successfully fetched and updated for the device"


class FileMessages(BaseMessageEnum):
    file_parse_trigger_success = "Parsing has been started"
    file_parse_conflict = "There is already parse processing started for file"
    file_actual_status_updated = "File actual status has been updated successfully"


class CoTerminusMessages(BaseMessageEnum):
    check_is_running = "The coterminous check is running"
    check_start_success = "The coterminous check has been started"
    check_results_save_success = "The coterminous check results has been stored"
    check_is_not_started = "The coterminous check is not started"
    check_is_not_running = "The coterminous check is not running now"
    check_is_aborted = "The coterminous check has been stopped successfully"


class NotificationMessages(BaseMessageEnum):
    mark_as_read_success = "Notification has been successfully marked as read"
    delete_success = "Notification has been successfully removed"


class TelemetryMessages(BaseMessageEnum):
    connection_name_already_exists = "Connection with such name already exists"
    connection_create_success = "Connection has been successfully created"
    connection_update_success = "Connection has been successfully updated"
    connection_delete_success = "Connection has been successfully deleted"
    token_validation_failed = "Invalid credentials. Please check and try again."
    site_mapping_create_success = "Site mapping has been created"
    site_mapping_already_exists = "Site mapping already exists"
    device_mapping_already_exists = "Device mapping already exists"
    das_provider_unavailable = "DAS provider is temporarily unavailable. Please try again later."


class AlertMessages(BaseMessageEnum):
    alert_create_success = "Alert has been successfully created"
    alert_update_success = "Alert has been successfully updated"
    alert_already_exists = "Alert already exists"


class TaskMessages(BaseMessageEnum):
    task_create_success = "Task has been successfully created"
    task_update_success = "Updated successfully"
    alert_task_already_exists = "Task for Alert already exists. Only one task can be created per alert"
    summary_of_event_not_applicable = "The section is applicable only for O&M and Asset Management modules"
    site_visit_not_applicable = "The feature is applicable only for O&M site level tasks"
    multiple_site_visits_error = "You can have only one site visit per task"
    site_visit_create_success = "Site visit has been successfully created"
    site_visit_not_found = "There is no site visit linked to the current task"
    site_visit_update_success = "Site visit has been successfully updated"


class BoardMessages(BaseMessageEnum):
    invalid_alert_task_board = (
        "Alert tasks are only allowed for Site O&M boards. "
        "Please either provide correct O&M board or remove alert_id from payload"
    )


class DocumentMessages(BaseMessageEnum):
    document_create_success = "Document has been successfully created"
    document_update_success = "Updated successfully"
    document_key_update_success = "Document key has been successfully updated"
    document_remove_success = "Document has been successfully removed"


class SiteMessages(BaseMessageEnum):
    site_update_success = "Site has been updated successfully"


class ChatBotMessages(BaseMessageEnum):
    ai_api_error = "An error occurred during ChatBot API call"


class PowerBIMessages(BaseMessageEnum):
    service_unavailable = "Power BI integration is temporarily unavailable. Please try again later."
