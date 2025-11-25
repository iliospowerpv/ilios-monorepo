resource "google_service_account" "cleanup_function_account" {
  project      = var.project_id
  account_id   = "backend-cleanup-account"
  display_name = "Service Account for App Engine cleanup function"
}

resource "google_service_account" "cleanup_function_trigger_account" {
  project      = var.project_id
  account_id   = "backend-cleanup-tr-account"
  display_name = "Service Account for App Engine cleanup function trigger"
}

resource "google_project_iam_member" "cleanup_function_account_access" {
  project = var.project_id
  role    = "roles/appengine.serviceAdmin"
  member  = "serviceAccount:${google_service_account.cleanup_function_account.email}"
}

resource "google_project_iam_member" "cleanup_function_trigger_account_access" {
  project = var.project_id
  role    = "roles/cloudfunctions.invoker"
  member  = "serviceAccount:${google_service_account.cleanup_function_trigger_account.email}"
}

resource "google_storage_bucket" "cloud_functions_bucket" {
  name     = "cloudfunctions-${var.project_id}"
  location = var.region
  project  = var.project_id
}

resource "google_storage_bucket_object" "cleanup_function_code" {
  name   = "app-engine-backend-cleanup.zip"
  bucket = google_storage_bucket.cloud_functions_bucket.name
  source = "/workspace/ilios-infra/functions/packages/app-engine-backend-cleanup.zip"
}

resource "google_cloudfunctions_function" "cleanup_function" {
  name                         = "app-engine-backend-cleanup"
  description                  = "Cloud Function for App Engine backend service versions cleanup"
  project                      = var.project_id
  region                       = var.region
  runtime                      = "python310"
  available_memory_mb          = 256
  source_archive_bucket        = google_storage_bucket.cloud_functions_bucket.name
  source_archive_object        = google_storage_bucket_object.cleanup_function_code.name
  trigger_http                 = true
  https_trigger_security_level = "SECURE_ALWAYS"
  timeout                      = 120
  entry_point                  = "handler"
  service_account_email        = google_service_account.cleanup_function_account.email
  environment_variables = {
    PROJECT_ID = var.project_id
  }
}

resource "google_cloudfunctions_function_iam_member" "cleanup_function_trigger_permissions" {
  project        = google_cloudfunctions_function.cleanup_function.project
  region         = google_cloudfunctions_function.cleanup_function.region
  cloud_function = google_cloudfunctions_function.cleanup_function.name
  role           = "roles/cloudfunctions.invoker"
  member         = "serviceAccount:${google_service_account.cleanup_function_trigger_account.email}"
}

resource "google_cloud_scheduler_job" "cleanup_function_trigger" {
  name        = "app-engine-backend-cleanup-trigger"
  description = "Schedule the Cloud Function for App Engine backend service versions cleanup"
  schedule    = "0 0 * * 0"
  project     = google_cloudfunctions_function.cleanup_function.project
  region      = google_cloudfunctions_function.cleanup_function.region

  http_target {
    uri         = google_cloudfunctions_function.cleanup_function.https_trigger_url
    http_method = "POST"
    oidc_token {
      audience              = "${google_cloudfunctions_function.cleanup_function.https_trigger_url}"
      service_account_email = google_service_account.cleanup_function_trigger_account.email
    }
  }
}