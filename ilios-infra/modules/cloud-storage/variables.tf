variable "project_id" {
  type = string
}

variable "random_suffix" {
  type    = bool
  default = false
}

variable "buckets" {
  type = list(object({
    name                        = string
    location                    = string
    random_suffix               = optional(bool, true)
    force_destroy               = optional(bool, false)
    storage_class               = optional(string)
    requester_pays              = optional(bool)
    uniform_bucket_level_access = optional(bool, true)
    labels                      = optional(map(string))
    cdn = optional(object({
      name = string
    }))
    iam_members = optional(list(object({
      name  = string
      roles = list(string)
    })))
    lifecycle_rule = optional(object({
      action = object({
        type          = string
        storage_class = optional(string)
      })
      condition = object({
        age                        = optional(number)
        created_before             = optional(string)
        with_state                 = optional(string)
        matches_storage_class      = optional(string)
        num_newer_versions         = optional(number)
        custom_time_before         = optional(string)
        days_since_custom_time     = optional(number)
        days_since_noncurrent_time = optional(number)
        noncurrent_time_before     = optional(string)
      })
    }))
    versioning = optional(object({
      enabled = bool
    }))
    website = optional(object({
      main_page_suffix = optional(string)
      not_found_page   = optional(string)
    }))
    cors = optional(object({
      origin          = optional(list(string))
      method          = optional(list(string))
      response_header = optional(list(string))
      max_age_seconds = optional(number)
    }))
    retention_policy = optional(object({
      retention_period = number
      is_locked        = optional(bool)
    }))
    logging = optional(object({
      log_bucket        = string
      log_object_prefix = optional(string)
    }))
    encryption = optional(object({
      default_kms_key_name = string
    }))
  }))
}
