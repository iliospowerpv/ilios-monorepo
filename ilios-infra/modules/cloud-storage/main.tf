resource "google_storage_bucket" "bucket" {
  for_each                    = local.buckets
  project                     = var.project_id
  name                        = var.random_suffix == true ? random_id.random_bucket_name[each.value.name].hex : each.value.name
  location                    = each.value.location
  force_destroy               = each.value.force_destroy
  storage_class               = each.value.storage_class
  labels                      = each.value.labels
  requester_pays              = each.value.requester_pays
  uniform_bucket_level_access = each.value.uniform_bucket_level_access

  dynamic "lifecycle_rule" {
    for_each = each.value.lifecycle_rule != null ? [each.value.lifecycle_rule] : []
    content {
      dynamic "action" {
        for_each = lifecycle_rule.value.action
        content {
          type          = action.value.type
          storage_class = action.value.storage_class
        }
      }

      dynamic "condition" {
        for_each = lifecycle_rule.value.condition
        content {
          age                        = condition.value.age
          created_before             = condition.value.created_before
          with_state                 = condition.value.with_state
          matches_storage_class      = condition.value.matches_storage_class
          num_newer_versions         = condition.value.num_newer_versions
          custom_time_before         = condition.value.custom_time_before
          days_since_custom_time     = condition.value.days_since_custom_time
          days_since_noncurrent_time = condition.value.days_since_noncurrent_time
          noncurrent_time_before     = condition.value.noncurrent_time_before
        }
      }
    }
  }

  dynamic "versioning" {
    for_each = each.value.versioning != null ? [each.value.versioning] : []
    content {
      enabled = versioning.value.enabled
    }
  }

  dynamic "website" {
    for_each = each.value.website != null ? [each.value.website] : []
    content {
      main_page_suffix = website.value.main_page_suffix
      not_found_page   = website.value.not_found_page
    }
  }

  dynamic "cors" {
    for_each = each.value.cors != null ? [each.value.cors] : []
    content {
      origin          = cors.value.origin
      method          = cors.value.method
      response_header = cors.value.response_header
      max_age_seconds = cors.value.max_age_seconds
    }
  }

  dynamic "retention_policy" {
    for_each = each.value.retention_policy != null ? [each.value.retention_policy] : []
    content {
      retention_period = retention_policy.value.retention_period
      is_locked        = retention_policy.value.is_locked
    }
  }

  dynamic "logging" {
    for_each = each.value.logging != null ? [each.value.logging] : []
    content {
      log_bucket        = logging.value.log_bucket
      log_object_prefix = logging.value.log_object_prefix
    }
  }

  dynamic "encryption" {
    for_each = each.value.encryption != null ? [each.value.encryptio] : []
    content {
      default_kms_key_name = encryption.value.default_kms_key_name
    }
  }
}

resource "random_id" "random_bucket_name" {
  for_each    = local.buckets
  prefix      = "${each.key}-"
  byte_length = 4
}

resource "google_storage_bucket_iam_member" "member" {
  for_each = local.bucket_iam_members
  bucket   = google_storage_bucket.bucket[each.value.bucket].name
  role     = each.value.role
  member   = each.value.name
}

resource "google_compute_backend_bucket" "backend" {
  for_each = { for k, v in local.cdn : v.name => k if can(v.name) }

  project     = var.project_id
  name        = each.key
  description = "Contains beautiful images"
  bucket_name = google_storage_bucket.bucket[each.value].name
  enable_cdn  = true
}

#TODO clarify cdn params

#resource "google_storage_bucket_iam_member" "bucket" {
#  for_each = { for k,v in local.cdn : v.name => k if can(v.name) }
#  bucket = google_storage_bucket.bucket[each.value].name
#  role   = "roles/storage.legacyObjectReader"
#  member = "serviceAccount:service-${data.google_project.project.number}@cloud-cdn-fill.iam.gserviceaccount.com"
#  //member = "allUsers"
#}


data "google_project" "project" {
  project_id = var.project_id
}
