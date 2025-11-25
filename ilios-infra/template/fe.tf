locals {
  lb_custom_response_headers = [
    "Strict-Transport-Security: max-age=31536000; includeSubDomains",
#    "Content-Security-Policy: default-src 'self' https://fonts.gstatic.com; script-src 'unsafe-inline' 'self' 'unsafe-eval' https://*.appcues.com https://cdn.cookielaw.org https://*.appcues.net ${join(" ", [for k, v in local.mfe_services : "https://${v.prefix}.cdn.${var.frontend_host_name[local.env]}"])} https://aurora-sdk.s3.amazonaws.com https://*.cloudfront.net https://cdn.segment.com https://*.usersnap.com https://*.hubspot.com https://js.hscollectedforms.net https://js.hsadspixel.net https://*.hs-scripts.com https://js.hs-banner.com https://js.hs-analytics.net https://forms.hsforms.com https://*.usemessages.com https://www.google-analytics.com https://cdn.amplitude.com https://*.hotjar.com https://cdn.jsdelivr.net https://www.google.com https://maps.googleapis.com https://edge.fullstory.com https://fonts.googleapis.com https://www.googletagmanager.com https://www.gstatic.com data: blob:; style-src 'unsafe-inline' 'self' https://*.appcues.com https://*.appcues.net ${join(" ", [for k, v in local.mfe_services : "https://${v.prefix}.cdn.${var.frontend_host_name[local.env]}"])} https://*.hotjar.com https://fonts.googleapis.com https://www.googletagmanager.com https://fonts.google.com; img-src 'self' https://*.appcues.com https://*.appcues.net https://cdn.cookielaw.org res.cloudinary.com cdn.jsdelivr.net https://www.gravatar.com https://www.google.nl https://*.hsforms.com https://*.hotjar.com https://*.hubspot.com https://www.google.bg https://maps.googleapis.com https://storage.googleapis.com https://www.googletagmanager.com https://www.google-analytics.com https://www.google.com https://www.google.com.ua data: blob:; connect-src 'self' 'unsafe-inline' 'unsafe-eval' https://privacyportal.onetrust.com https://*.appcues.com https://cdn.cookielaw.org https://*.appcues.net wss://*.appcues.net wss://*.appcues.com https://edge.fullstory.com https://logs.browser-intake-datadoghq.com https://*.auslr.io  https://*.launchdarkly.com https://api.segment.io https://cdn.segment.com https://*.aurorasolar.com https://*.pusher.com wss://*.pusher.com https://${var.backend_pricing_host_name[local.env]} wss://${var.hotifications_host_name[local.env]} https://${var.hotifications_host_name[local.env]} https://*.amazonaws.com https://*.usersnap.com https://*.ingest.sentry.io https://vc.hotjar.io https://*.analytics.google.com https://*.hubspot.com https://*.hubapi.com https://region.js https://stats.g.doubleclick.net https://analytics.google.com https://api.amplitude.com wss://*.hotjar.com https://*.hotjar.com https://*.hotjar.io https://storage.googleapis.com https://www.google-analytics.com https://rs.fullstory.com https://maps.googleapis.com https://${var.backend_host_name[local.env]} https://${var.backend_whp_host_name[local.env]} https://ssoext${var.env_prefix[local.env]}.gaf.com data: blob:; frame-src 'self' https://*.appcues.com https://*.hubspot.com https://www.google.com https://vars.hotjar.com https://ssoext${var.env_prefix[local.env]}.gaf.com https://${local.env == "prod" ? "webto" : "test"}.salesforce.com; frame-ancestors 'none'; font-src 'self' https://fonts.gstatic.com https://*.hotjar.com ${join(" ", [for k, v in local.mfe_services : "https://${v.prefix}.cdn.${var.frontend_host_name[local.env]}"])} data:; worker-src 'self' blob:"
  ]
}

resource "google_storage_bucket" "frontend-storage" {
  name          = "${var.environment}-ilios-bucket"
  location      = "US"
  storage_class = "MULTI_REGIONAL"
  project       = var.project_id
  versioning {
    enabled = "false"
  }
  force_destroy = "true"
  website {
    main_page_suffix = "index.html"
    not_found_page   = "index.html"
  }
}

resource "google_storage_bucket_access_control" "public_rule" {
  bucket = google_storage_bucket.frontend-storage.id
  role   = "READER"
  entity = "allUsers"
}


#
##resource "google_storage_bucket_iam_binding" "fe" {
##  bucket = google_storage_bucket.frontend-storage.name
##  role   = "roles/storage.admin"
##  members = [
##    "serviceAccount:${google_service_account.circle_ci.email}",
##  ]
##}
#
# https://github.com/hashicorp/terraform-provider-google/issues/10622
resource "google_compute_backend_bucket" "frontend-backend-bucket" {
  provider = google-beta
  project       = var.project_id
  name        = "frontend-${var.environment}-ilios"
  bucket_name = google_storage_bucket.frontend-storage.name
  enable_cdn  = true
  cdn_policy {
    cache_mode                   = "CACHE_ALL_STATIC"
    client_ttl                   = 3600
    default_ttl                  = 3600
    max_ttl                      = 86400
    negative_caching             = true
    serve_while_stale            = 0
    signed_url_cache_max_age_sec = 0
    request_coalescing           = true
  }
  custom_response_headers = concat([
    "X-Frame-Options:DENY"
  ], local.lb_custom_response_headers)
}
#
##resource "google_compute_backend_bucket" "salesforce_email_assets_backend_bucket" {
##  name        = "salesforce-assets-${local.env}-${local.env == "dev" ? "gaf-energy" : "gafenergy"}"
##  bucket_name = google_storage_bucket.email_assets.name
##
##  enable_cdn = true
##  cdn_policy {
##    cache_mode                   = "CACHE_ALL_STATIC"
##    client_ttl                   = 3600
##    default_ttl                  = 3600
##    max_ttl                      = 86400
##    negative_caching             = true
##    serve_while_stale            = 0
##    signed_url_cache_max_age_sec = 0
##    request_coalescing           = true
##  }
##}

resource "google_compute_global_address" "frontend-static-ip" {
  name          = "frontend-${var.environment}-ilios"
  project       = var.project_id
}

resource "google_compute_url_map" "frontend-urlmap" {
  name            = "frontend-${var.environment}-ilios"
  project       = var.project_id
  default_service = google_compute_backend_bucket.frontend-backend-bucket.self_link

#  host_rule {
#    hosts        = [var.frontend_host_name[local.env]]
#    path_matcher = "partner-portal-fe"
#  }

#  path_matcher {
#    name            = "partner-portal-fe"
#    default_service = google_compute_backend_bucket.frontend-backend-bucket.self_link
#
#    path_rule {
#      paths   = ["/sf-assets/*"]
#      service = google_compute_backend_bucket.salesforce_email_assets_backend_bucket.self_link
#    }
#  }

  test {
    description = "Ilios Frontend"
#    host        = var.frontend_host_name[local.env]
    host        = "test.com"
    path        = "/"
    service     = google_compute_backend_bucket.frontend-backend-bucket.self_link
  }

#  test {
#    description = "GAFE Salesforce email assets"
#    host        = var.frontend_host_name[local.env]
#    path        = "/sf-assets"
#    service     = google_compute_backend_bucket.salesforce_email_assets_backend_bucket.self_link
#  }
}

resource "google_compute_ssl_policy" "https-frontend-ssl-policy" {
  name            = "frontend-${var.environment}-ilios"
  project         = var.project_id
  min_tls_version = "TLS_1_2"
  profile         = "RESTRICTED"
}

resource "google_compute_target_http_proxy" "http-frontend-target-proxy" {
  name    = "http-frontend-${var.environment}-ilios-target-proxy-http"
  project         = var.project_id
  url_map = google_compute_url_map.frontend-urlmap.self_link
}

resource "google_compute_managed_ssl_certificate" "frontend" {
  name    = "frontend"
  project = var.project_id

  managed {
    domains = ["${var.environment}.iliospower.com"]
  }
}

resource "google_compute_target_https_proxy" "https-frontend-target-proxy" {
  name    = "https-frontend-${var.environment}-ilios-target-proxy-https"
  project = var.project_id
  url_map = google_compute_url_map.frontend-urlmap.self_link
  ssl_certificates = [
    google_compute_managed_ssl_certificate.frontend.id,
  ]
  ssl_policy    = google_compute_ssl_policy.https-frontend-ssl-policy.name
  quic_override = "NONE"
}

resource "google_compute_global_forwarding_rule" "http-frontend-forwarding-rule" {
  name        = "http-frontend-${var.environment}-ilios"
  project     = var.project_id
  target      = google_compute_target_http_proxy.http-frontend-target-proxy.self_link
  ip_address  = google_compute_global_address.frontend-static-ip.address
  port_range  = "80"
  ip_protocol = "TCP"
}

resource "google_compute_global_forwarding_rule" "https-frontend-forwarding-rule" {
  name        = "https-frontend-${var.environment}-ilios"
  project     = var.project_id
  target      = google_compute_target_https_proxy.https-frontend-target-proxy.self_link
  ip_address  = google_compute_global_address.frontend-static-ip.address
  port_range  = "443"
  ip_protocol = "TCP"
}
