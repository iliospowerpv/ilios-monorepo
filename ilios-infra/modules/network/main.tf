module "vpc" {
  source  = "terraform-google-modules/network/google"
  version = "~> 6.0.0"

  project_id                             = var.project_id
  network_name                           = var.network_name
  description                            = var.description
  auto_create_subnetworks                = var.auto_create_subnetworks
  delete_default_internet_gateway_routes = var.delete_default_internet_gateway_routes
  mtu                                    = var.mtu
  routes                                 = var.routes
  routing_mode                           = var.routing_mode
  shared_vpc_host                        = var.shared_vpc_host

  subnets = var.subnets
}

module "firewall_rules" {
  source  = "terraform-google-modules/network/google//modules/firewall-rules"
  version = "~> 6.0.0"

  project_id   = var.project_id
  network_name = module.vpc.network_name

  rules = var.firewall_rules
}
