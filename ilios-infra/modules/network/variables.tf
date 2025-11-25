variable "project_id" {
}

variable "description" {
  type    = string
  default = ""
}

variable "subnet_private_access" {
  type    = string
  default = false
}

variable "subnet_flow_logs" {
  type    = string
  default = false
}

variable "subnet_flow_logs_interval" {
  type    = string
  default = "INTERVAL_5_SEC"
}

variable "subnet_flow_logs_sampling" {
  type    = string
  default = 0.7
}

variable "subnet_flow_logs_metadata" {
  type    = string
  default = "INCLUDE_ALL_METADATA"
}

variable "routes" {
  default = []
}

variable "network_name" {}

variable "routing_mode" {}

variable "subnets" {}

variable "region" {}

variable "auto_create_subnetworks" {}

variable "delete_default_internet_gateway_routes" {}

variable "firewall_rules" {
  default = []
}

variable "mtu" {}

variable "shared_vpc_host" {
  default = false
}