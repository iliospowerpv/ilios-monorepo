## VPC network
#resource "google_compute_network" "ilb_network" {
#  name                    = "l7-ilb-network"
#  provider                = google-beta
#  auto_create_subnetworks = false
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## proxy-only subnet
#resource "google_compute_subnetwork" "proxy_subnet" {
#  name          = "l7-ilb-proxy-subnet"
#  provider      = google-beta
#  ip_cidr_range = "10.0.0.0/24"
#  region        = "europe-west1"
#  purpose       = "REGIONAL_MANAGED_PROXY"
#  role          = "ACTIVE"
#  network       = google_compute_network.ilb_network.id
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## backend subnet
#resource "google_compute_subnetwork" "ilb_subnet" {
#  name          = "l7-ilb-subnet"
#  provider      = google-beta
#  ip_cidr_range = "10.0.1.0/24"
#  region        = "europe-west1"
#  network       = google_compute_network.ilb_network.id
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## forwarding rule
#resource "google_compute_forwarding_rule" "google_compute_forwarding_rule" {
#  name                  = "l7-ilb-forwarding-rule"
#  provider              = google-beta
#  region                = "europe-west1"
#  depends_on            = [google_compute_subnetwork.proxy_subnet]
#  ip_protocol           = "TCP"
#  load_balancing_scheme = "INTERNAL_MANAGED"
#  port_range            = "80"
#  target                = google_compute_region_target_http_proxy.default.id
#  network               = google_compute_network.ilb_network.id
#  subnetwork            = google_compute_subnetwork.ilb_subnet.id
#  network_tier          = "PREMIUM"
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## HTTP target proxy
#resource "google_compute_region_target_http_proxy" "default" {
#  name     = "l7-ilb-target-http-proxy"
#  provider = google-beta
#  region   = "europe-west1"
#  url_map  = google_compute_region_url_map.default.id
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## URL map
#resource "google_compute_region_url_map" "default" {
#  name            = "l7-ilb-regional-url-map"
#  provider        = google-beta
#  region          = "europe-west1"
#  default_service = google_compute_region_backend_service.default.id
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## backend service
#resource "google_compute_region_backend_service" "default" {
#  name                  = "l7-ilb-backend-subnet"
#  provider              = google-beta
#  region                = "europe-west1"
#  protocol              = "HTTP"
#  load_balancing_scheme = "INTERNAL_MANAGED"
#  timeout_sec           = 10
#  health_checks         = [google_compute_region_health_check.default.id]
#  backend {
#    group           = google_compute_region_instance_group_manager.mig.instance_group
#    balancing_mode  = "UTILIZATION"
#    capacity_scaler = 1.0
#  }
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## instance template
#resource "google_compute_instance_template" "instance_template" {
#  name         = "l7-ilb-mig-template"
#  provider     = google-beta
#  machine_type = "e2-small"
#  tags         = ["http-server"]
#
#  network_interface {
#    network    = google_compute_network.ilb_network.id
#    subnetwork = google_compute_subnetwork.ilb_subnet.id
#    access_config {
#      # add external ip to fetch packages
#    }
#  }
#  disk {
#    source_image = "debian-cloud/debian-10"
#    auto_delete  = true
#    boot         = true
#  }
#
#  # install nginx and serve a simple web page
#  metadata = {
#    startup-script = <<-EOF1
#      #! /bin/bash
#      set -euo pipefail
#
#      export DEBIAN_FRONTEND=noninteractive
#      apt-get update
#      apt-get install -y nginx-light jq
#
#      NAME=$(curl -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/hostname")
#      IP=$(curl -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/ip")
#      METADATA=$(curl -f -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/attributes/?recursive=True" | jq 'del(.["startup-script"])')
#
#      cat <<EOF > /var/www/html/index.html
#      <pre>
#      Name: $NAME
#      IP: $IP
#      Metadata: $METADATA
#      </pre>
#      EOF
#    EOF1
#  }
#  lifecycle {
#    create_before_destroy = true
#  }
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## health check
#resource "google_compute_region_health_check" "default" {
#  name     = "l7-ilb-hc"
#  provider = google-beta
#  region   = "europe-west1"
#  http_health_check {
#    port_specification = "USE_SERVING_PORT"
#  }
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## MIG
#resource "google_compute_region_instance_group_manager" "mig" {
#  name     = "l7-ilb-mig1"
#  provider = google-beta
#  region   = "europe-west1"
#  version {
#    instance_template = google_compute_instance_template.instance_template.id
#    name              = "primary"
#  }
#  base_instance_name = "vm"
#  target_size        = 2
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## allow all access from IAP and health check ranges
#resource "google_compute_firewall" "fw_iap" {
#  name          = "l7-ilb-fw-allow-iap-hc"
#  provider      = google-beta
#  direction     = "INGRESS"
#  network       = google_compute_network.ilb_network.id
#  source_ranges = ["130.211.0.0/22", "35.191.0.0/16", "35.235.240.0/20"]
#  allow {
#    protocol = "tcp"
#  }
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## allow http from proxy subnet to backends
#resource "google_compute_firewall" "fw_ilb_to_backends" {
#  name          = "l7-ilb-fw-allow-ilb-to-backends"
#  provider      = google-beta
#  direction     = "INGRESS"
#  network       = google_compute_network.ilb_network.id
#  source_ranges = ["10.0.0.0/24"]
#  target_tags   = ["http-server"]
#  allow {
#    protocol = "tcp"
#    ports    = ["80", "443", "8080"]
#  }
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## test instance
#resource "google_compute_instance" "vm_test" {
#  name         = "l7-ilb-test-vm"
#  provider     = google-beta
#  zone         = "europe-west1-b"
#  machine_type = "e2-small"
#  network_interface {
#    network    = google_compute_network.ilb_network.id
#    subnetwork = google_compute_subnetwork.ilb_subnet.id
#  }
#  boot_disk {
#    initialize_params {
#      image = "debian-cloud/debian-10"
#    }
#  }
#  project           = module.project_creation["Dev"].project_ids.project_id
#}




# VPC
#resource "google_compute_network" "default" {
#  name                    = "l7-xlb-network"
#  provider                = google-beta
#  auto_create_subnetworks = false
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## backend subnet
#resource "google_compute_subnetwork" "default" {
#  name          = "l7-xlb-subnet"
#  provider      = google-beta
#  ip_cidr_range = "10.0.1.0/24"
#  region        = "us-central1"
#  network       = google_compute_network.default.id
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## reserved IP address
#resource "google_compute_global_address" "default" {
#  provider = google-beta
#  name     = "l7-xlb-static-ip"
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## forwarding rule
#resource "google_compute_global_forwarding_rule" "default" {
#  name                  = "l7-xlb-forwarding-rule"
#  provider              = google-beta
#  ip_protocol           = "TCP"
#  load_balancing_scheme = "EXTERNAL"
#  port_range            = "80"
#  target                = google_compute_target_http_proxy.default.id
#  ip_address            = google_compute_global_address.default.id
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## http proxy
#resource "google_compute_target_http_proxy" "default" {
#  name     = "l7-xlb-target-http-proxy"
#  provider = google-beta
#  url_map  = google_compute_url_map.default.id
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## url map
#resource "google_compute_url_map" "default" {
#  name            = "l7-xlb-url-map"
#  provider        = google-beta
#  default_service = google_compute_backend_service.default.id
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## backend service with custom request and response headers
#resource "google_compute_backend_service" "default" {
#  name                    = "l7-xlb-backend-service"
#  provider                = google-beta
#  protocol                = "HTTP"
#  port_name               = "my-port"
#  load_balancing_scheme   = "EXTERNAL"
#  timeout_sec             = 10
#  enable_cdn              = true
#  custom_request_headers  = ["X-Client-Geo-Location: {client_region_subdivision}, {client_city}"]
#  custom_response_headers = ["X-Cache-Hit: {cdn_cache_status}"]
#  health_checks           = [google_compute_health_check.default.id]
#  backend {
#    group           = google_compute_instance_group_manager.default.instance_group
#    balancing_mode  = "UTILIZATION"
#    capacity_scaler = 1.0
#  }
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## instance template
#resource "google_compute_instance_template" "default" {
#  name         = "l7-xlb-mig-template"
#  provider     = google-beta
#  machine_type = "e2-small"
#  tags         = ["allow-health-check"]
#
#  network_interface {
#    network    = google_compute_network.default.id
#    subnetwork = google_compute_subnetwork.default.id
#    access_config {
#      # add external ip to fetch packages
#    }
#  }
#  disk {
#    source_image = "debian-cloud/debian-10"
#    auto_delete  = true
#    boot         = true
#  }
#
#  # install nginx and serve a simple web page
#  metadata = {
#    startup-script = <<-EOF1
#      #! /bin/bash
#      set -euo pipefail
#
#      export DEBIAN_FRONTEND=noninteractive
#      apt-get update
#      apt-get install -y nginx-light jq
#
#      NAME=$(curl -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/hostname")
#      IP=$(curl -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/ip")
#      METADATA=$(curl -f -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/attributes/?recursive=True" | jq 'del(.["startup-script"])')
#
#      cat <<EOF > /var/www/html/index.html
#      <pre>
#      Name: $NAME
#      IP: $IP
#      Metadata: $METADATA
#      </pre>
#      EOF
#    EOF1
#  }
#  lifecycle {
#    create_before_destroy = true
#  }
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## health check
#resource "google_compute_health_check" "default" {
#  name     = "l7-xlb-hc"
#  provider = google-beta
#  http_health_check {
#    port_specification = "USE_SERVING_PORT"
#  }
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## MIG
#resource "google_compute_instance_group_manager" "default" {
#  name     = "l7-xlb-mig1"
#  provider = google-beta
#  zone     = "us-central1-c"
#  named_port {
#    name = "http"
#    port = 8080
#  }
#  version {
#    instance_template = google_compute_instance_template.default.id
#    name              = "primary"
#  }
#  base_instance_name = "vm"
#  target_size        = 2
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
#
## allow access from health check ranges
#resource "google_compute_firewall" "default" {
#  name          = "l7-xlb-fw-allow-hc"
#  provider      = google-beta
#  direction     = "INGRESS"
#  network       = google_compute_network.default.id
#  source_ranges = ["130.211.0.0/22", "35.191.0.0/16"]
#  allow {
#    protocol = "tcp"
#  }
#  target_tags = ["allow-health-check"]
#  project           = module.project_creation["Dev"].project_ids.project_id
#}
## allow SSH
#resource "google_compute_firewall" "fw_ilb_ssh" {
#  name      = "l4-ilb-fw-ssh"
#  direction = "INGRESS"
#  network   = google_compute_network.default.id
#  allow {
#    protocol = "tcp"
#    ports    = ["22","80","443"]
#  }
#  target_tags   = ["allow-ssh"]
#  source_ranges = ["0.0.0.0/0"]
#  project           = module.project_creation["Dev"].project_ids.project_id
#}