resource "google_compute_network" "default" {
  name                    = "ilios-internal-network"
  auto_create_subnetworks = false
  project                 = var.project_id
}

# backend subnet
resource "google_compute_subnetwork" "default" {
  name          = "ilios-internal-subnetwork"
  ip_cidr_range = "10.10.0.0/24"
  region        = var.region
  network       = google_compute_network.default.id
  project       = var.project_id
  private_ip_google_access = true
}

resource "google_compute_subnetwork" "default-triggers" {
  name          = "ilios-internal-subnetwork-trigers"
  ip_cidr_range = "10.10.10.0/24"
  region        = "us-central1"
  network       = google_compute_network.default.id
  project       = var.project_id
  private_ip_google_access = true
}