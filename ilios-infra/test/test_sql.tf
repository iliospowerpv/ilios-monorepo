##module "sql-db" {
##  source  = "GoogleCloudPlatform/sql-db/google"
##  version = "19.0.0"
##}
#
#/**
# * Copyright 2019 Google LLC
# *
# * Licensed under the Apache License, Version 2.0 (the "License");
# * you may not use this file except in compliance with the License.
# * You may obtain a copy of the License at
# *
# *      http://www.apache.org/licenses/LICENSE-2.0
# *
# * Unless required by applicable law or agreed to in writing, software
# * distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# * See the License for the specific language governing permissions and
# * limitations under the License.
# */
#
#locals {
#  read_replica_ip_configuration = {
#    ipv4_enabled       = true
#    require_ssl        = false
#    private_network    = null
#    allocated_ip_range = null
#    authorized_networks = [
#      {
#        name  = "${var.project_id}-cidr"
#        value = var.mysql_ha_external_ip_range
#      },
#    ]
#  }
#
#}
#
#
#module "mysql" {
#  source  = "terraform-google-modules/sql-db/google//modules/mysql"
#  version = "~> 18.0"
#
#  name                 = var.mysql_ha_name
#  random_instance_name = true
#  project_id           = var.project_id
#  database_version     = "MYSQL_5_7"
#  region               = "us-central1"
#
#  deletion_protection = false
#
#  // Master configurations
#  tier                            = "db-n1-standard-1"
#  zone                            = "us-central1-c"
#  availability_type               = "REGIONAL"
#  maintenance_window_day          = 7
#  maintenance_window_hour         = 12
#  maintenance_window_update_track = "stable"
#
#  database_flags = [{ name = "long_query_time", value = 1 }]
#
#  user_labels = {
#    foo = "bar"
#  }
#
#  ip_configuration = {
#    ipv4_enabled       = true
#    require_ssl        = true
#    private_network    = null
#    allocated_ip_range = null
#    authorized_networks = [
#      {
#        name  = "${var.project_id}-cidr"
#        value = var.mysql_ha_external_ip_range
#      },
#    ]
#  }
#
#  password_validation_policy_config = {
#    enable_password_policy      = true
#    complexity                  = "COMPLEXITY_DEFAULT"
#    disallow_username_substring = true
#    min_length                  = 8
#  }
#
#  backup_configuration = {
#    enabled                        = true
#    binary_log_enabled             = true
#    start_time                     = "20:55"
#    location                       = null
#    transaction_log_retention_days = null
#    retained_backups               = 365
#    retention_unit                 = "COUNT"
#  }
#
#  // Read replica configurations
#  read_replica_name_suffix = "-test-ha"
#  replica_database_version = "MYSQL_5_7"
#  read_replicas = [
#    {
#      name                  = "0"
#      zone                  = "us-central1-a"
#      availability_type     = "ZONAL"
#      tier                  = "db-n1-standard-1"
#      ip_configuration      = local.read_replica_ip_configuration
#      database_flags        = [{ name = "long_query_time", value = 1 }]
#      disk_autoresize       = null
#      disk_autoresize_limit = null
#      disk_size             = null
#      disk_type             = "PD_HDD"
#      user_labels           = { bar = "baz" }
#      encryption_key_name   = null
#    },
#    {
#      name                  = "1"
#      zone                  = "us-central1-b"
#      availability_type     = "ZONAL"
#      tier                  = "db-n1-standard-1"
#      ip_configuration      = local.read_replica_ip_configuration
#      database_flags        = [{ name = "long_query_time", value = 1 }]
#      disk_autoresize       = null
#      disk_autoresize_limit = null
#      disk_size             = null
#      disk_type             = "PD_HDD"
#      user_labels           = { bar = "baz" }
#      encryption_key_name   = null
#    },
#    {
#      name                  = "2"
#      zone                  = "us-central1-c"
#      availability_type     = "ZONAL"
#      tier                  = "db-n1-standard-1"
#      ip_configuration      = local.read_replica_ip_configuration
#      database_flags        = [{ name = "long_query_time", value = 1 }]
#      disk_autoresize       = null
#      disk_autoresize_limit = null
#      disk_size             = null
#      disk_type             = "PD_HDD"
#      user_labels           = { bar = "baz" }
#      encryption_key_name   = null
#    },
#  ]
#
#  db_name      = var.mysql_ha_name
#  db_charset   = "utf8mb4"
#  db_collation = "utf8mb4_general_ci"
#
#  additional_databases = [
#    {
#      name      = "${var.mysql_ha_name}-additional"
#      charset   = "utf8mb4"
#      collation = "utf8mb4_general_ci"
#    },
#  ]
#
#  user_name     = "tftest"
#  user_password = "Example!12345"
#  root_password = ".5nHITPioEJk^k}="
#
#  additional_users = [
#    {
#      name            = "tftest2"
#      password        = "Example!12345"
#      host            = "localhost"
#      type            = "BUILT_IN"
#      random_password = false
#    },
#    {
#      name            = "tftest3"
#      password        = "Example!12345"
#      host            = "localhost"
#      type            = "BUILT_IN"
#      random_password = false
#    },
#  ]
#}
























##module "sql-db" {
##  source  = "GoogleCloudPlatform/sql-db/google"
##  version = "19.0.0"
##}
#
#/**
# * Copyright 2019 Google LLC
# *
# * Licensed under the Apache License, Version 2.0 (the "License");
# * you may not use this file except in compliance with the License.
# * You may obtain a copy of the License at
# *
# *      http://www.apache.org/licenses/LICENSE-2.0
# *
# * Unless required by applicable law or agreed to in writing, software
# * distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# * See the License for the specific language governing permissions and
# * limitations under the License.
# */
#
#locals {
#  read_replica_ip_configuration = {
#    ipv4_enabled       = true
#    require_ssl        = false
#    private_network    = null
#    allocated_ip_range = null
#    authorized_networks = [
#      {
#        name  = "${module.project_creation["Dev"].project_ids.project_id}-cidr"
#        value = "[0.0.0.0/0]"
#      },
#    ]
#  }
#
#}
#
#
#module "mysql" {
#  source  = "terraform-google-modules/sql-db/google//modules/mysql"
#  version = "~> 18.0"
#
#  name                 = "test123"
#  random_instance_name = true
#  project_id           = module.project_creation["Dev"].project_ids.project_id
#  database_version     = "MYSQL_5_7"
#  region               = "us-central1"
#
#  deletion_protection = false
#
#  // Master configurations
#  tier                            = "db-n1-standard-1"
#  zone                            = "us-central1-c"
#  availability_type               = "REGIONAL"
#  maintenance_window_day          = 7
#  maintenance_window_hour         = 12
#  maintenance_window_update_track = "stable"
#
#  database_flags = [{ name = "long_query_time", value = 1 }]
#
#  user_labels = {
#    foo = "bar"
#  }
#
#  ip_configuration = {
#    ipv4_enabled       = true
#    require_ssl        = true
#    private_network    = null
#    allocated_ip_range = null
#    authorized_networks = [
#      {
#        name  = "${module.project_creation["Dev"].project_ids.project_id}-cidr"
#        value = "0.0.0.0/0"
#      },
#    ]
#  }
#
#  password_validation_policy_config = {
#    enable_password_policy      = true
#    complexity                  = "COMPLEXITY_DEFAULT"
#    disallow_username_substring = true
#    min_length                  = 8
#  }
#
#  backup_configuration = {
#    enabled                        = true
#    binary_log_enabled             = true
#    start_time                     = "20:55"
#    location                       = null
#    transaction_log_retention_days = null
#    retained_backups               = 365
#    retention_unit                 = "COUNT"
#  }
#
#  // Read replica configurations
#  read_replica_name_suffix = "-test-ha"
#  replica_database_version = "MYSQL_5_7"
#  read_replicas = [
#    {
#      name                  = "0"
#      zone                  = "us-central1-a"
#      availability_type     = "ZONAL"
#      tier                  = "db-n1-standard-1"
#      ip_configuration      = local.read_replica_ip_configuration
#      database_flags        = [{ name = "long_query_time", value = 1 }]
#      disk_autoresize       = null
#      disk_autoresize_limit = null
#      disk_size             = null
#      disk_type             = "PD_HDD"
#      user_labels           = { bar = "baz" }
#      encryption_key_name   = null
#    },
#    {
#      name                  = "1"
#      zone                  = "us-central1-b"
#      availability_type     = "ZONAL"
#      tier                  = "db-n1-standard-1"
#      ip_configuration      = local.read_replica_ip_configuration
#      database_flags        = [{ name = "long_query_time", value = 1 }]
#      disk_autoresize       = null
#      disk_autoresize_limit = null
#      disk_size             = null
#      disk_type             = "PD_HDD"
#      user_labels           = { bar = "baz" }
#      encryption_key_name   = null
#    },
#    {
#      name                  = "2"
#      zone                  = "us-central1-c"
#      availability_type     = "ZONAL"
#      tier                  = "db-n1-standard-1"
#      ip_configuration      = local.read_replica_ip_configuration
#      database_flags        = [{ name = "long_query_time", value = 1 }]
#      disk_autoresize       = null
#      disk_autoresize_limit = null
#      disk_size             = null
#      disk_type             = "PD_HDD"
#      user_labels           = { bar = "baz" }
#      encryption_key_name   = null
#    },
#  ]
#
#  db_name      = "test123-ha"
#  db_charset   = "utf8mb4"
#  db_collation = "utf8mb4_general_ci"
#
#  additional_databases = [
#    {
#      name      = "test123-ha-additional"
#      charset   = "utf8mb4"
#      collation = "utf8mb4_general_ci"
#    },
#  ]
#
#  user_name     = "tftest"
#  user_password = "Example!12345"
#  root_password = ".5nHITPioEJk^k}="
#
#  additional_users = [
#    {
#      name            = "tftest2"
#      password        = "Example!12345"
#      host            = "localhost"
#      type            = "BUILT_IN"
#      random_password = false
#    },
#    {
#      name            = "tftest3"
#      password        = "Example!12345"
#      host            = "localhost"
#      type            = "BUILT_IN"
#      random_password = false
#    },
#  ]
#}


#THE WAY TO ADD A PASSWORD
#
#resource "random_password" "secret_vpn" {
#  length  = 24
#  special = false
#}
#
#resource "google_secret_manager_secret" "shared_secret" {
#  project   = module.project_creation[var.vpn_configuration.project_name].project_ids.project_id
#  secret_id = "${var.vpn_configuration.project_name}-shared-secret"
#  labels = {
#    label = "havpn-config"
#  }
#
#  replication {
#    automatic = true
#  }
#}
#
#resource "google_secret_manager_secret_version" "shared_secret_version" {
#  secret      = google_secret_manager_secret.shared_secret.id
#  secret_data = random_password.secret_vpn.result
#}
#
#  shared_secret      = random_password.secret_vpn.result



#locals {
#  read_replica_ip_configuration = {
#    ipv4_enabled       = true
#    require_ssl        = false
#    ssl_mode           = "ENCRYPTED_ONLY"
#    private_network    = null
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
#  region               = "us-central1"
#
#  // Master configurations
#  tier                            = "db-custom-1-3840"
#  zone                            = "us-central1-c"
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
#    ipv4_enabled       = true
#    require_ssl        = true
#    private_network    = null
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
#      zone                  = "us-central1-a"
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