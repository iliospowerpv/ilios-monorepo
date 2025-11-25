# resource "google_project" "my_project" {
#   name       = var.app_name
#   project_id = var.project_id
# }

resource "google_app_engine_application" "app" {
  project     = var.project_id
  location_id = var.location
}