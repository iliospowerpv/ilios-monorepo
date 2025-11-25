terraform {
  required_version = ">= 1.4.4"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "< 6.0, >= 3.83"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "< 6.0, >= 3.45"
    }
  }
}