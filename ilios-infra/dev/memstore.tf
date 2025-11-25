resource "google_redis_instance" "cache" {
  region                  = var.region
  project                 = var.project_id
  name                    = "cache"
  display_name            = "Redis"
  tier                    = "BASIC"
  memory_size_gb          = 1
  redis_version           = "REDIS_7_0"
  authorized_network      = google_compute_network.default.id
  connect_mode            = "DIRECT_PEERING"
  auth_enabled            = true
  transit_encryption_mode = "SERVER_AUTHENTICATION"

  labels = {
    environment = var.environment
  }

  persistence_config {
    persistence_mode    = "RDB"
    rdb_snapshot_period = "TWENTY_FOUR_HOURS"
  }

  maintenance_policy {
    weekly_maintenance_window {
      day = "SATURDAY"
      start_time {
        hours = 0
        minutes = 0
        seconds = 0
      }
    }
  }
}

resource "google_secret_manager_secret" "cache_creds_secret" {
  project   = var.project_id
  secret_id = "redis-creds"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "cache_certs_secret" {
  project   = var.project_id
  secret_id = "redis-certs"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "cache_certs_secret_version" {
  secret      = google_secret_manager_secret.cache_certs_secret.id
  secret_data = google_redis_instance.cache.server_ca_certs[0].cert
}