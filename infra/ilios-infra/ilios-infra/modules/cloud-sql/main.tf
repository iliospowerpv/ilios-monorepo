resource "google_sql_database_instance" "master_instance" {
  for_each            = local.instances_configs
  name                = contains(keys(local.instances_with_random_suffix), each.value.name) ? random_id.random_instance_name[each.value.name].dec : each.value.name
  project             = var.project_id
  region              = each.value.region
  database_version    = each.value.database_version
  deletion_protection = each.value.deletion_protection

  dynamic "settings" {
    for_each = each.value.settings == null ? [] : [each.value.settings]
    content {
      tier              = settings.value.tier
      activation_policy = settings.value.activation_policy
      availability_type = settings.value.availability_type
      collation         = settings.value.collation
      disk_autoresize   = settings.value.disk_autoresize
      disk_size         = settings.value.disk_size
      disk_type         = settings.value.disk_type
      pricing_plan      = settings.value.pricing_plan
      user_labels       = settings.value.user_labels

      dynamic "database_flags" {
        for_each = settings.value.database_flags == null ? [] : settings.value.database_flags
        content {
          name  = database_flags.value.name
          value = database_flags.value.value
        }
      }

      dynamic "backup_configuration" {
        for_each = settings.value.backup_configuration == null ? [] : [settings.value.backup_configuration]
        content {
          binary_log_enabled             = backup_configuration.value.binary_log_enabled
          enabled                        = backup_configuration.value.enabled
          start_time                     = backup_configuration.value.start_time
          point_in_time_recovery_enabled = backup_configuration.value.point_in_time_recovery_enabled
          location                       = backup_configuration.value.location
          transaction_log_retention_days = backup_configuration.value.transaction_log_retention_days

          dynamic "backup_retention_settings" {
            for_each = backup_configuration.value.backup_retention_settings == null ? [] : [backup_configuration.value.backup_retention_settings]
            content {
              retained_backups = backup_retention_settings.value.retained_backups
              retention_unit   = backup_retention_settings.value.retention_unit
            }
          }
        }
      }

      dynamic "ip_configuration" {
        for_each = settings.value.ip_configuration == null ? [] : [settings.value.ip_configuration]
        content {
          allocated_ip_range                            = try(ip_configuration.value.allocated_ip_range, null)
          ipv4_enabled                                  = try(ip_configuration.value.ipv4_enabled, null)
          private_network                               = ip_configuration.value.private_network
          enable_private_path_for_google_cloud_services = try(ip_configuration.value.private_path_for_google_api, null)
          require_ssl                                   = try(ip_configuration.value.require_ssl, null)

          dynamic "authorized_networks" {
            for_each = ip_configuration.value.authorized_networks == null ? [] : ip_configuration.value.authorized_networks
            content {
              expiration_time = authorized_networks.value.expiration_time
              name            = authorized_networks.value.name
              value           = authorized_networks.value.value
            }
          }
        }
      }

      dynamic "location_preference" {
        for_each = settings.value.location_preference == null ? [] : [settings.value.location_preference]
        content {
          follow_gae_application = location_preference.value.follow_gae_application
          zone                   = location_preference.value.zone
        }
      }

      dynamic "maintenance_window" {
        for_each = settings.value.maintenance_window == null ? [] : [settings.value.maintenance_window]
        content {
          day          = maintenance_window.value.day
          hour         = maintenance_window.value.hour
          update_track = maintenance_window.value.update_track
        }
      }

      dynamic "insights_config" {
        for_each = settings.value.insights_config == null ? [] : [settings.value.insights_config]
        content {
          query_insights_enabled  = insights_config.value.query_insights_enabled
          query_string_length     = insights_config.value.query_string_length
          record_application_tags = insights_config.value.record_application_tags
          record_client_address   = insights_config.value.record_client_address
        }
      }
    }
  }

  #depends_on = [
  #  google_service_networking_connection.private_vpc_connection
  #]
}

resource "random_id" "random_instance_name" {
  for_each    = local.instances_with_random_suffix
  prefix      = "${each.key}-"
  byte_length = each.value.length
}

resource "google_sql_database" "database" {
  for_each = local.databases_iterable
  project  = var.project_id
  name     = each.value.database
  instance = google_sql_database_instance.master_instance[each.value.instance].id
}

resource "random_password" "db_user_password" {
  for_each = local.users_iterable
  length   = 24
  special  = false
}

resource "google_sql_user" "db_user" {
  for_each = local.users_iterable
  project  = var.project_id
  name     = each.value.user
  instance = google_sql_database_instance.master_instance[each.value.instance].id
  password = random_password.db_user_password["${each.value.instance}:${each.value.user}"].result
}

resource "google_secret_manager_secret" "db_user_password" {
  for_each  = local.users_iterable
  project   = var.project_id
  secret_id = "${each.value.instance}-${each.value.user}"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
}

resource "google_secret_manager_secret_version" "db_user_password_version" {
  for_each = local.users_iterable

  secret      = google_secret_manager_secret.db_user_password[each.key].id
  secret_data = google_sql_user.db_user[each.key].password
}
