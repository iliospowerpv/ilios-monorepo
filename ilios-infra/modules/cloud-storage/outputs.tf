output "bucket" {
  value = { for bucket_key, bucket_config in google_storage_bucket.bucket : bucket_key => bucket_config }
}

output "cdn" {
  value = google_compute_backend_bucket.backend
}

output "test" {
  value = local.cdn
}