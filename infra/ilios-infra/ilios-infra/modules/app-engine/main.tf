resource "google_project" "my_project" {
  name       = var.app_name
  project_id = var.project
}

resource "google_app_engine_application" "app" {
  project     = google_project.my_project.project_id
  location_id = var.location
}