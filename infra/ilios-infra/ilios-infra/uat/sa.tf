# IAM role binding for App Engine default service account to access Cloud Storage
resource "google_project_iam_member" "app_engine_storage_access" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${var.project_id}@appspot.gserviceaccount.com"
}

# IAM role binding for App Engine default service account to access Cloud SQL
resource "google_project_iam_member" "app_engine_sql_access" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${var.project_id}@appspot.gserviceaccount.com"
}

resource "google_service_account_key" "app_engine_sa_key"{
    service_account_id = "${var.project_id}@appspot.gserviceaccount.com"
    public_key_type = "TYPE_X509_PEM_FILE"
}

resource "google_secret_manager_secret" "app_engine_secret" {
  secret_id = "app-sa-key"
  project = var.project_id

  labels = {
    label = "my-label"
  }

  replication {
    auto {}
  }

}

resource "google_secret_manager_secret_version" "app_engine_secret_password" {
  secret = google_secret_manager_secret.app_engine_secret.id
  secret_data = base64decode(google_service_account_key.app_engine_sa_key.private_key)
}






resource "google_service_account" "cloud_build_sa" {
  project      = var.project_id
  account_id   = "cloud-build-cust-svc-acct"
  display_name = "Cloud Build Custom Service Account"
}

resource "google_project_iam_member" "cloud_build_iam" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.editor"
  member  = "serviceAccount:${google_service_account.cloud_build_sa.email}"
}

resource "google_project_iam_member" "app_engine_admin" {
  project = var.project_id
  role    = "roles/appengine.appAdmin"
  member  = "serviceAccount:${google_service_account.cloud_build_sa.email}"
}

resource "google_project_iam_member" "cloud_build_service_account" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.builder"
  member  = "serviceAccount:${google_service_account.cloud_build_sa.email}"
}

resource "google_project_iam_member" "secret_manager_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_build_sa.email}"
}

resource "google_project_iam_member" "service_account_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.cloud_build_sa.email}"
}

resource "google_project_iam_member" "integrations_owner" {
  project = var.project_id
  role    = "roles/cloudbuild.integrations.owner"
  member  = "serviceAccount:${google_service_account.cloud_build_sa.email}"
}

resource "google_project_iam_member" "cloud_build_sa_owner" {
  project = var.project_id
  role    = "roles/owner"
  member  = "serviceAccount:${google_service_account.cloud_build_sa.email}"
}