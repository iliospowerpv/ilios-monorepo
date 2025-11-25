#https://github.com/terraform-google-modules/terraform-google-sql-db/tree/v19.0.0/examples/postgresql-ha
#https://github.com/terraform-google-modules/terraform-google-sql-db/tree/v19.0.0/modules/postgresql
#
#locals {
#  read_replica_ip_configuration = {
#    ipv4_enabled       = false
#    enable_private_path_for_google_cloud_services = true
#    require_ssl        = false
#    ssl_mode           = "ENCRYPTED_ONLY"
#    private_network    = "projects/${var.project_id}/global/networks/l7-xlb-network"
#    allocated_ip_range = null
#    authorized_networks = [
#      {
#        name  = "${var.project_id}-cidr"
#        value = var.pg_ha_external_ip_range
#      },
#    ]
#  }
#}
#
#module "pg" {
#  source  = "terraform-google-modules/sql-db/google//modules/postgresql"
#  version = "~> 18.0"
#
#  name                 = var.pg_ha_name
#  random_instance_name = true
#  project_id           = var.project_id
#  database_version     = "POSTGRES_9_6"
#  region               = var.region
#
#  // Master configurations
#  tier                            = "db-custom-1-3840"
#  zone                            = "${var.region}-c"
#  availability_type               = "REGIONAL"
#  maintenance_window_day          = 7
#  maintenance_window_hour         = 12
#  maintenance_window_update_track = "stable"
#
#  deletion_protection = false
#
#  database_flags = [{ name = "autovacuum", value = "off" }]
#
#  user_labels = {
#    foo = "bar"
#  }
#
#  ip_configuration = {
#    ipv4_enabled       = false
#    enable_private_path_for_google_cloud_services = true
#    require_ssl        = true
#    private_network    = "projects/${var.project_id}/global/networks/l7-xlb-network"
#    allocated_ip_range = null
#    authorized_networks = [
#      {
#        name  = "${var.project_id}-cidr"
#        value = var.pg_ha_external_ip_range
#      },
#    ]
#  }
#
#  backup_configuration = {
#    enabled                        = true
#    start_time                     = "20:55"
#    location                       = null
#    point_in_time_recovery_enabled = false
#    transaction_log_retention_days = null
#    retained_backups               = 365
#    retention_unit                 = "COUNT"
#  }
#
#  // Read replica configurations
#  read_replica_name_suffix = "-test-ha"
#  read_replicas = [
#    {
#      name                  = "0"
#      zone                  = "${var.region}-a"
#      availability_type     = "REGIONAL"
#      tier                  = "db-custom-1-3840"
#      ip_configuration      = local.read_replica_ip_configuration
#      database_flags        = [{ name = "autovacuum", value = "off" }]
#      disk_autoresize       = null
#      disk_autoresize_limit = null
#      disk_size             = null
#      disk_type             = "PD_HDD"
#      user_labels           = { bar = "baz" }
#      encryption_key_name   = null
#    },
#  ]
#
#  db_name      = var.pg_ha_name
#  db_charset   = "UTF8"
#  db_collation = "en_US.UTF8"
#
#  additional_databases = [
#    {
#      name      = "${var.pg_ha_name}-additional"
#      charset   = "UTF8"
#      collation = "en_US.UTF8"
#    },
#  ]
#
#  user_name     = "tftest"
#  user_password = "foobar"
#
#  additional_users = [
#    {
#      name            = "tftest2"
#      password        = "abcdefg"
#      host            = "localhost"
#      random_password = false
#    },
#    {
#      name            = "tftest3"
#      password        = "abcdefg"
#      host            = "localhost"
#      random_password = false
#    },
#  ]
#}

#======================================================================
data "google_compute_network" "default" {
  name    = "ilios-internal-network"
  project = var.project_id
}

resource "google_compute_global_address" "private_ip_address" {
  provider      = google
  name          = "private-ip-address"
  project       = var.project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = data.google_compute_network.default.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  provider                = google
  network                 = data.google_compute_network.default.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

resource "random_id" "db_name_suffix" {
  byte_length = 4
}

resource "google_sql_database_instance" "main" {
  name             = "test-db"
  project = var.project_id
  database_version = "POSTGRES_15"
  region           = var.region

  depends_on = [google_service_networking_connection.private_vpc_connection]

  settings {
    availability_type = "REGIONAL"
    user_labels       = var.labels
    tier              = "db-custom-2-8192"
    disk_size         = "10"
    disk_type         = "PD_SSD"
    disk_autoresize   = "true"
    ip_configuration {
      ipv4_enabled    = "false"
      private_network = data.google_compute_network.default.id
      enable_private_path_for_google_cloud_services = true
    }
  }
}

resource "google_sql_database_instance" "chart_bot" {
  name             = "chatbot-vector-store-${var.environment}"
  project          = var.project_id
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    availability_type = "ZONAL"
    user_labels       = var.labels
    tier              = "db-custom-2-8192"
    disk_size         = "10"
    disk_type         = "PD_SSD"
    disk_autoresize   = "true"
    ip_configuration {
      ipv4_enabled    = "false"
      private_network = data.google_compute_network.default.id
    }
  }

  depends_on = [google_service_networking_connection.private_vpc_connection]
}

resource "google_sql_database" "chart_bot_database" {
  name     = "chatbot-documents"
  project  = var.project_id
  instance = google_sql_database_instance.chart_bot.name
}

resource "google_sql_user" "chart_bot_database_user" {
  name     = "chatbot"
  project  = var.project_id
  instance = google_sql_database_instance.chart_bot.name
  password = "temporary"
}