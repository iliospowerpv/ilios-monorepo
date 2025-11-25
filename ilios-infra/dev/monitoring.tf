# resource "google_monitoring_monitored_project" "monitoring" {
#   metrics_scope = "locations/global/metricsScopes/${var.monitoring-project}"
#   name          = var.project_id
# }