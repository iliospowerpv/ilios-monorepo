resource "google_organization_iam_member" "organization" {
  for_each = { for role in var.roles : role => var.member }
  org_id  = var.org_id
  role    = each.key
  member  = format("%s:%s@%s", "group", var.member, var.domain)
}