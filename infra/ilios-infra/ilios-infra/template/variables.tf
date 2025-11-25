variable "project_id" {
  type        = string
  description = "The project to run tests against"
  default     = proj_id
}

variable "region" {
  type        = string
  default     = "us-central1"
}

variable "location" {
  type        = string
  default     = "us-central"
}

variable "app_name" {
  type        = string
  default     = "backend"
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
  default     = env
}

variable "labels" {
  default     = {
    environment = lab
  }
}

variable "monitoring-project" {
  default     = "prj-monitoring-base-7cd8"
}