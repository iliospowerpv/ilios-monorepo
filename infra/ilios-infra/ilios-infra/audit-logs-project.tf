module "audit_project" {
  source  = "terraform-google-modules/project-factory/google"
  version = "~> 14.1.0"

  name                               = var.audit_conf.project_name
  org_id                             = var.organization_id
  billing_account                    = var.billing_account
  random_project_id                  = true
  lien                               = false
  default_service_account            = "keep"
  create_project_sa                  = true
  grant_services_security_admin_role = true
  activate_apis = [
    "bigquery.googleapis.com",
    "logging.googleapis.com",
  ]
}

module "bigquery_export" {
  source  = "terraform-google-modules/log-export/google"
  version = "7.4.2"

  log_sink_name          = var.audit_conf.log_sink_name
  destination_uri        = module.bigquery_destination.destination_uri
  filter                 = var.audit_conf.filter
  parent_resource_id     = var.organization_id
  parent_resource_type   = var.audit_conf.parent_resource_type
  unique_writer_identity = true
  include_children       = true

  depends_on = [module.audit_project]
}

module "bigquery_destination" {
  source  = "terraform-google-modules/log-export/google//modules/bigquery"
  version = "7.4.2"


  dataset_name             = var.audit_conf.dataset_name
  project_id               = module.audit_project.project_id
  location                 = var.audit_conf.location
  log_sink_writer_identity = module.bigquery_export.writer_identity
  expiration_days          = 365
}


# IAM Audit log configs to enable collection of all possible audit logs.
resource "google_organization_iam_audit_config" "config" {
  org_id  = var.organization_id
  service = "allServices"

  audit_log_config {
    log_type = "DATA_READ"
  }
  audit_log_config {
    log_type = "DATA_WRITE"
  }
  audit_log_config {
    log_type = "ADMIN_READ"
  }
}

resource "google_project_iam_member" "logs_viewers_auditors" {
  project = module.audit_project.project_id
  role    = "roles/bigquery.user"
  member  = module.bigquery_export.writer_identity
}

# add need roles to group
resource "google_organization_iam_member" "security_auditors" {
  org_id = var.organization_id
  role   = "roles/iam.securityReviewer"
  member = module.bigquery_export.writer_identity
}
