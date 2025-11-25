#resource "google_compute_ssl_policy" "ssl-policy" {
#  name            = "ssl-policy"
#  profile         = "MODERN"
#  min_tls_version = "TLS_1_2"
#}
#
##resource "google_compute_region_network_endpoint_group" "negs_backend" {
##  for_each              = toset(var.containers_locations)
##  name                  = "backend-neg-${each.value}"
##  network_endpoint_type = "SERVERLESS"
##  region                = google_cloud_run_service.backend_services[each.key].location
##  cloud_run {
##    service = google_cloud_run_service.backend_services[each.key].name
##  }
##}
#NEED TO CHOOSE NEGS
#resource "google_compute_region_network_endpoint_group" "region_network_endpoint_group_internet_ip_port" {
#  name                  = "ip-port-neg"
#  region                = "us-central1"
#  network               = google_compute_network.default.id
#
#  network_endpoint_type = "INTERNET_IP_PORT"
#}
#
#variable "backend_domain" {
#	type        = string
#	description = "Domain name to run the load balancer on."
#	default     = "maria.iliospower.com"
#}
#
#module "lb_backend" {
#  source            = "GoogleCloudPlatform/lb-http/google//modules/serverless_negs"
#
#  project           = module.project_creation["Dev"].project_ids.project_id
#  name              = "lb-backend"
#
#  ssl                             = true
#  https_redirect                  = true
#  managed_ssl_certificate_domains = [var.backend_domain]
#  ssl_policy                      = google_compute_ssl_policy.ssl-policy.self_link
#
#  backends = {
#    default = {
#      description                     = null
#      enable_cdn                      = false
#      custom_request_headers          = null
#      security_policy                 = null
#
#
#      log_config = {
#        enable = true
#        sample_rate = 1.0
#      }
#
##      groups = [
##        for neg in google_compute_region_network_endpoint_group.negs_backend:
##        {
##          group = neg.id
##        }
##      ]
#
#      iap_config = {
#        enable               = false
#        oauth2_client_id     = null
#        oauth2_client_secret = null
#      }
#    }
#  }
#}







#THIS IS FOR ONLY TEST PURPOSES
#module "gce-lb-http" {
#  source            = "GoogleCloudPlatform/lb-http/google"
#  version           = "~> 9.0"
#
#  project           = module.project_creation["Dev"].project_ids.project_id
#  name              = "group-http-lb"
##  target_tags       = [module.mig1.target_tags, module.mig2.target_tags]
#  backends = {
#    default = {
#      port                            = "80"
#      protocol                        = "HTTP"
#      port_name                       = "portname"
#      timeout_sec                     = 10
#      enable_cdn                      = false
#
#
#      health_check = {
#        request_path        = "/"
#        port                = "80"
#      }
#
#      log_config = {
#        enable = true
#        sample_rate = 1.0
#      }
#
#      groups = [
#        {
#          # Each node pool instance group should be added to the backend.
#          group                        = "instance-group-1"
#        },
#      ]
#
#      iap_config = {
#        enable               = false
#      }
#    }
#  }
#}