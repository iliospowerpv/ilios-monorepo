resource "google_storage_bucket" "file-storage" {
  name          = "${var.environment}-due-diligence-files"
  location      = "US"
  storage_class = "MULTI_REGIONAL"
  project       = var.project_id
  versioning {
    enabled = "false"
  }
  force_destroy = "true"

  cors {
      max_age_seconds = 3600
      method          = [
        "PUT",
        "GET",
        "HEAD",
        "DELETE",
        "POST",
        "OPTIONS",
          ]
        origin          = [
            "*",
          ]
        response_header = [
            "Content-Type",
            "Access-Control-Allow-Origin",
            "x-goog-resumable",
          ]
      }
}


resource "google_storage_bucket" "task-tracker-attachments" {
  name          = "${var.environment}-task-tracker-attachments"
  location      = "US"
  storage_class = "MULTI_REGIONAL"
  project       = var.project_id
  versioning {
    enabled = "false"
  }

  cors {
        max_age_seconds = 3600
        method          = [
          "PUT",
          "GET",
          "HEAD",
          "DELETE",
          "POST",
          "OPTIONS",
            ]
          origin          = [
              "*",
            ]
          response_header = [
              "Content-Type",
              "Access-Control-Allow-Origin",
              "x-goog-resumable",
            ]
        }


  force_destroy = "true"
}

resource "google_storage_bucket_access_control" "task-tracker-attachments_public_rule" {
  bucket = google_storage_bucket.task-tracker-attachments.id
  role   = "READER"
  entity = "allUsers"
}


#############  device-documents  #############
resource "google_storage_bucket" "device-documents" {
  name          = "${var.environment}-device-documents"
  location      = "US"
  storage_class = "MULTI_REGIONAL"
  project       = var.project_id
  versioning {
    enabled = "false"
  }

  cors {
        max_age_seconds = 3600
        method          = [
          "PUT",
          "GET",
          "HEAD",
          "DELETE",
          "POST",
          "OPTIONS",
            ]
          origin          = [
              "*",
            ]
          response_header = [
              "Content-Type",
              "Access-Control-Allow-Origin",
              "x-goog-resumable",
            ]
        }


  force_destroy = "true"
}

resource "google_storage_bucket_access_control" "device-documents_public_rule" {
  bucket = google_storage_bucket.device-documents.id
  role   = "READER"
  entity = "allUsers"
}


#############  site-visit-uploads  #############
resource "google_storage_bucket" "site-visit-uploads" {
  name          = "${var.environment}-site-visit-uploads"
  location      = "US"
  storage_class = "MULTI_REGIONAL"
  project       = var.project_id
  versioning {
    enabled = "false"
  }
  cors {
      max_age_seconds = 3600
      method          = [
        "PUT",
        "GET",
        "HEAD",
        "DELETE",
        "POST",
        "OPTIONS",
          ]
        origin          = [
            "*",
          ]
        response_header = [
            "Content-Type",
            "Access-Control-Allow-Origin",
            "x-goog-resumable",
          ]
      }
  force_destroy = "true"
}


#module "gcs_buckets" {
#  source  = "terraform-google-modules/cloud-storage/google"
#  version = "~> 5.0"
#  project_id  = "<PROJECT ID>"
#  names = ["first"]
##  names = ["first", "second"]
#  prefix = "my-unique-prefix"
#  set_admin_roles = true
#  admins = ["group:foo-admins@example.com"]
#  versioning = {
#    first = true
#  }
#  bucket_admins = {
#    second = "user:spam@example.com,user:eggs@example.com"
#  }
#}

##https://stackoverflow.com/questions/72861431/how-to-deploy-a-gcp-https-load-balancer-via-terraform-lb-http-module-that-only
#module "gcs_buckets" {
#  source  = "terraform-google-modules/cloud-storage/google"
#  version = "~> 5.0"
#  project_id  = var.project_id
#  location = var.region
#  names = ["first-123456"]
##  names = ["first", "second"]
#  prefix = "ilios"
#  set_admin_roles = true
##  admins = ["group:softserveinc@iliospower.com"]
#  versioning = {
#    first-123456 = true
#  }
##  bucket_admins = {
##    second = "user:spam@example.com,user:eggs@example.com"
##  }
#  force_destroy = {
#    first-123456 = true
#  }
#}