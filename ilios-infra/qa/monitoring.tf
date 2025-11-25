# data "google_compute_global_address" "frontend-static-ip" {
#   name  = "frontend-${var.environment}-ilios"
#   project = var.project_id
# }

# resource "google_monitoring_monitored_project" "monitoring" {
#   metrics_scope = "locations/global/metricsScopes/${var.monitoring-project}"
#   name          = var.project_id
# }


# # resource "google_monitoring_alert_policy" "alert_policy" {
# #   display_name = "My Alert Policy"
# #   combiner     = "OR"
# #   project = var.project_id
# #   conditions {
# #     display_name = "test condition"
# #     condition_threshold {
# #       filter     = "metric.type=\"compute.googleapis.com/instance/disk/write_bytes_count\" AND resource.type=\"gce_instance\""
# #       duration   = "60s"
# #       comparison = "COMPARISON_GT"
# #       aggregations {
# #         alignment_period   = "60s"
# #         per_series_aligner = "ALIGN_RATE"
# #       }
# #     }
# #   }

# #   user_labels = {
# #     foo = "bar"
# #   }
# # }


# resource "google_monitoring_uptime_check_config" "frontend" {
#   display_name = "http-uptime-check"
#   timeout      = "60s"
#   project = var.monitoring-project

#   tcp_check {
#     port = 80
#     ping_config {
#       pings_count = 2
#     }
#   }

#   monitored_resource {
#     type = "uptime_url"
#     labels = {
#       host       = data.google_compute_global_address.frontend-static-ip.address
#     }
#   }

#   checker_type = "STATIC_IP_CHECKERS"
# }

# resource "google_monitoring_uptime_check_config" "app_engine_tcp_check" {
#   project = var.monitoring-project
#   display_name = "App Engine TCP Uptime Check"

#   timeout = "10s"
#   period  = "60s"

#   tcp_check {
#     port = 443
#   }

#   monitored_resource {
#     type   = "uptime_url"
#     labels = {
#       project_id = var.project_id
#       host       = "backend-dot-${var.project_id}.appspot.com"  # Formatted as <service>-dot-<project_id>.appspot.com
#     }
#   }

#   # Define the locations from which the check should be performed
#   selected_regions = [
#     "USA",
#     "EUROPE"
#   ]

# }