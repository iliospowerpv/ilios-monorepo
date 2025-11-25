#data "terraform_remote_state" "data_folders" {
#  backend = "local"
#  config = {
##    prefix = "data"
#    path = "../terraform-folders.tfstate"
#  }
#}

#data "terraform_remote_state" "data_folders" {
#  backend = "gcs"
#  config = {
#    bucket = "cft-tfstate-c21e"
#    prefix = "terraform/infra-state"
#  }
#}

module "bootstrap" {
  source  = "terraform-google-modules/bootstrap/google"
  version = "6.3.0"

  org_id                 = var.organization_id
  billing_account        = var.billing_account
#  folder_id              = data.terraform_remote_state.data_folders.outputs.folder_ids[var.bootstrap_configuration.folder_root].folders_param.folders_map[var.bootstrap_configuration.folder_belong].folder_id
  project_id             = var.bootstrap_configuration.project_name
  create_terraform_sa    = var.bootstrap_configuration.terraform_sa
  group_org_admins       = var.bootstrap_configuration.group_org_admins
  group_billing_admins   = var.bootstrap_configuration.group_billing_admins
  default_region         = var.region
  sa_org_iam_permissions = var.bootstrap_configuration.sa_org_iam_permissions
}

#resource "null_resource" "replace" {
#  provisioner "local-exec" {
#    command     = "sed -i 's/UNIFIED-BUCKET/$WORD/g' ./backend.tf"
#    interpreter = ["/bin/bash", "-c"]
#    environment = { WORD = module.bootstrap.gcs_bucket_tfstate }
#  }
#}