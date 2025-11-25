
module "project" {
  source  = "terraform-google-modules/project-factory/google"
  version = "14.1.0"

  name              = var.project_name
  random_project_id = true
  org_id            = var.org_id
  folder_id         = var.folder_id
  billing_account   = var.billing_account

  #CHANGE TO TRUE
  lien = false

  # Create and keep default service accounts when certain APIs are enabled.
  # delete, deprivilege, disable, or keep.
  default_service_account = "keep"

  # Do not create an additional project service account to be used for Compute Engine.
  create_project_sa = false
  activate_apis     = var.apis_list
}