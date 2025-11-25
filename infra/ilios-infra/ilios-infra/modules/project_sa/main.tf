resource "google_service_account" "app_sa" {
  count        = length(var.account_id) > 0 ? 1 : 0
  project      = var.project
  account_id   = var.account_id
  display_name = "Project VM Service Account"
}

resource "google_project_iam_member" "project-roles" {
  project  = var.project
  for_each = length(var.sa_permissions[0]) > 0 ? { for role in var.sa_permissions : role => var.account_id } : {}
  role     = each.key
  #member   = "${var.member}:${google_service_account.app_sa[0].email}"
  member = "${var.member}:${try(google_service_account.app_sa[0].email, var.user)}"
}