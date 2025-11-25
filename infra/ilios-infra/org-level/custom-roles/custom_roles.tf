resource "google_organization_iam_member" "billing_admins" {
  org_id  = var.org_id
  role    = var.permissions_billing_admins
  member  = "group:${var.group_email[7]}"
}

resource "google_organization_iam_member" "org_admins" {
  org_id  = var.org_id
  for_each   = toset(var.permissions_org_admins)
  role    = each.key
  member  = "group:${var.group_email[0]}"
}

resource "google_organization_iam_member" "org_browsers" {
  org_id  = var.org_id
  for_each   = toset(var.permissions_org_browsers)
  role    = each.key
  member  = "group:${var.group_email[13]}"
}

resource "google_organization_iam_member" "org_viewers" {
  org_id  = var.org_id
  for_each   = toset(var.permissions_org_viewers)
  role    = each.key
  member  = "group:${var.group_email[12]}"
}

resource "google_organization_iam_member" "billing_viewers" {
  org_id  = var.org_id
  for_each   = toset(var.permissions_billing_viewers)
  role    = each.key
  member  = "group:${var.group_email[8]}"
}

resource "google_organization_iam_member" "security_admins" {
  org_id  = var.org_id
  for_each   = toset(var.permissions_security_admins)
  role    = each.key
  member  = "group:${var.group_email[8]}"
}
