module "project_folders" {
  for_each = var.folders
  source   = "./modules/folder_creation"

  parent_id          = format("organizations/%s", var.organization_id)
  root_folder        = each.value.root_name
  nested_folder      = each.value.nested_names
  per_folder_admins  = each.value.per_folder_admins
  all_folder_admins  = each.value.all_folder_admins
  folder_admin_roles = each.value.folder_admin_roles

#  folder_admin_roles = concat(each.value.folder_admin_roles, ["serviceAccount:${data.terraform_remote_state.sa_name.outputs.terraform_sa_email}"])
}

module "project_creation" {
  for_each        = var.projects
  source          = "./modules/project_creation"
  folder_id       = module.project_folders[each.value.folder_root].folders_param.folders_map[each.value.folder_belong].folder_id
  billing_account = var.billing_account
  org_id          = var.organization_id
  apis_list       = each.value.api_list
  project_name    = each.value.project_name
}

module "secret_project" {
  source  = "terraform-google-modules/project-factory/google"
  version = "~> 14.1.0"

  name                               = "prj-secret"
  org_id                             = var.organization_id
  billing_account                    = var.billing_account
  random_project_id                  = true
  lien                               = false
  default_service_account            = "keep"
  create_project_sa                  = true
  grant_services_security_admin_role = true
  activate_apis = [
    "secretmanager.googleapis.com",
  ]
}

#
#
#module "vpc" {
#  for_each = var.vpcs_configuration
#  source   = "./modules/network"
#
#  project_id                             = module.project_creation[each.key].project_ids.project_id
#  network_name                           = each.value.network_name
#  routing_mode                           = each.value.routing_mode
#  auto_create_subnetworks                = each.value.auto_create_subnetworks
#  delete_default_internet_gateway_routes = each.value.delete_default_internet_gateway_routes
#  subnets                                = each.value.subnets
#  mtu                                    = each.value.mtu
#  region                                 = var.region
#  shared_vpc_host                        = each.value.shared_vpc_host
#  firewall_rules                         = each.value.firewall_rules
#}
#
#module "gcv_vpc" {
#  for_each = var.gcv_vpc_configuration
#  source   = "terraform-google-modules/network/google//modules/vpc"
#  version  = "6.0.0"
#
#  project_id   = module.project_creation[each.key].project_ids.project_id
#  network_name = each.value.network_name
#}
#
#module "network-peering" {
#  for_each = var.peer_config
#  source   = "terraform-google-modules/network/google//modules/network-peering"
#  version  = "6.0.0"
#
#  prefix                                   = each.key
#  export_local_custom_routes               = each.value.export_local_custom_routes
#  export_peer_custom_routes                = each.value.export_peer_custom_routes
#  local_network                            = module.vpc[each.value.local_network].vpc_config.network_self_link
#  peer_network                             = module.vpc[each.value.peer_network].vpc_config.network_self_link
#  export_peer_subnet_routes_with_public_ip = true
#}
#
#module "cloud_router" {
#  for_each = var.cloud_nat_configuration
#  source   = "terraform-google-modules/cloud-router/google"
#  version  = "~> 4.0"
#
#  name    = each.value.router_name
#  project = module.project_creation[each.key].project_ids.project_id
#  region  = each.value.region
#  network = module.vpc[each.key].vpc_config.network_name
#  #  nats    = each.value.nats
#  /*bgp = {
#    asn               = each.value.router_asn
#    advertise_mode    = each.value.advertise_mode
#    advertised_groups = each.value.advertised_groups
#  }
#*/
#
#  depends_on = [module.vpc]
#}
#
#module "project_sa" {
#  for_each = var.sa_permissions
#  source   = "./modules/project_sa"
#
#  project        = module.project_creation[each.value.project_belong].project_ids.project_id
#  sa_permissions = try(each.value.roles, [""])
#  account_id     = try(format("%s-%s", replace(each.key, "_", "-"), each.value.account_id), "")
#  member         = each.value.member
#  user           = try(each.value.user, "")
#}
#
#module "org_roles" {
#  for_each = var.organization_role
#  source = "./modules/organization_role"
#
#  org_id = var.organization_id
#  roles   = each.value.roles
#  member  = each.key
#  domain =  each.value.domain
#}
#
#data "terraform_remote_state" "sa_name" {
#  backend = "gcs"
#  config = {
#    bucket = "cft-tfstate-c21e"
#    prefix = "terraform/terraform-bootstrap"
#  }
#}
