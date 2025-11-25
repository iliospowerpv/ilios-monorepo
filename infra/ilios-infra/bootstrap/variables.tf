variable "billing_account" {
  type    = string
  default = "01FF9F-7E0C2A-5E9C35"
}

variable "organization_id" {
  type    = string
  default = "9240743021"
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "bootstrap_configuration" {
  type = object({
    project_name           = string
#    folder_root            = string
#    folder_belong          = string
    group_org_admins       = string
    group_billing_admins   = string
    terraform_sa           = bool
    sa_org_iam_permissions = list(string)
  })
  default = {
    project_name         = "prj-admin-p-base"
    group_org_admins     = "softserveinc@iliospower.com"
    group_billing_admins = "softserveinc1@iliospower.com"
#    folder_root          = "common"
#    folder_belong        = "fldr-management"
    terraform_sa         = true
    sa_org_iam_permissions = [
      "roles/billing.user",
      "roles/compute.networkAdmin",
      "roles/compute.xpnAdmin",
      "roles/iam.securityAdmin",
      "roles/iam.serviceAccountAdmin",
      "roles/logging.configWriter",
      "roles/orgpolicy.policyAdmin",
      "roles/resourcemanager.folderAdmin",
      "roles/resourcemanager.organizationViewer",
      "roles/resourcemanager.projectIamAdmin",
      "roles/resourcemanager.organizationAdmin",
      "roles/serviceusage.serviceUsageAdmin",
      "roles/resourcemanager.projectIamAdmin",
      "roles/logging.admin",
    ]
  }
}
