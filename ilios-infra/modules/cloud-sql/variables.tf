variable "project_id" {
  type = string
}

variable "region" {}

variable "cloud_sql_configuration" {
  type = list(object({
    name = string
    random_suffix = optional(object({
      length = number
    }))
    region              = string
    database_version    = string
    databases           = optional(list(string))
    users               = optional(list(string))
    deletion_protection = optional(bool)
    settings = optional(object({
      tier              = string
      activation_policy = optional(string)
      availability_type = optional(string)
      collation         = optional(string)
      disk_autoresize   = optional(bool)
      disk_size         = optional(number)
      disk_type         = optional(string)
      pricing_plan      = optional(string)
      user_labels       = optional(map(string))
      database_flags = optional(list(object({
        name  = string
        value = string
      })))
      backup_configuration = optional(object({
        binary_log_enabled             = optional(bool)
        enabled                        = optional(bool, true)
        start_time                     = optional(string, "15:00")
        point_in_time_recovery_enabled = optional(bool, true)
        location                       = optional(string, "EU")
        transaction_log_retention_days = optional(number, 7)
        backup_retention_settings = optional(object({
          retained_backups = optional(any, 7)
          retention_unit   = optional(string, "COUNT")
        }))
      }))
      ip_configuration = optional(object({
        ipv4_enabled                = optional(bool, false)
        allocated_ip_range          = optional(string)
        private_network             = optional(string)
        require_ssl                 = optional(bool)
        private_path_for_google_api = optional(bool)
        authorized_networks = optional(list(object({
          expiration_time = optional(number)
          name            = optional(string)
          value           = string
        })))
      }))
      location_preference = optional(object({
        follow_gae_application = optional(string)
        zone                   = optional(string)
      }))
      maintenance_window = optional(object({
        day          = optional(number)
        hour         = optional(number)
        update_track = optional(string)
      }))
      insights_config = optional(object({
        query_insights_enabled  = bool
        query_string_length     = number
        record_application_tags = bool
        record_client_address   = bool
      }))
    }))
  }))
}
