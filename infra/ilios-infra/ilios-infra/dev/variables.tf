variable "project_id" {
  type        = string
  description = "The project to run tests against"
  default     = "prj-dev-base-e61d"
}

variable "region" {
  type        = string
  default     = "us-west1"
}

variable "pg_ha_name" {
  type        = string
  description = "The name for Cloud SQL instance"
  default     = "tf-pg-ha"
}

variable "pg_ha_external_ip_range" {
  type        = string
  description = "The ip range to allow connecting from/to Cloud SQL"
  default     = "192.10.10.10/32"
}

variable "environment" {
  default     = "dev"
}

variable "labels" {
  default     = {
    environment = "dev"
  }
}

variable "monitoring-project" {
  default     = "prj-monitoring-base-7cd8"
}