variable "billing_account" {
  type = string
}

variable "organization_id" {
  type = string
}

variable "region" {
  type = string
}


variable "folders" {
  type = map(object({
    root_name          = string
    nested_names       = list(string)
    per_folder_admins  = optional(map(string))
    all_folder_admins  = optional(list(string))
    folder_admin_roles = optional(list(string))
  }))
}

variable "projects" {
  type = map(object({
    project_name      = string
    folder_root       = optional(string)
    folder_belong     = optional(string)
    create_project_sa = string
    api_list          = list(string)
  }))
}

variable "audit_conf" {
  type = object({
    project_name         = string
    location             = string
    parent_resource_type = string
    filter               = string
    log_sink_name        = string
    dataset_name         = string
    auditors_group       = string
  })
}

#variable "vpcs_configuration" {
#  type = map(object({
#    network_name                           = optional(string)
#    shared_vpc_host                        = optional(bool)
#    auto_create_subnetworks                = optional(bool)
#    delete_default_internet_gateway_routes = optional(bool)
#    mtu                                    = optional(number)
#    routing_mode                           = optional(string)
#    subnets = list(object({
#      subnet_region         = string
#      subnet_name           = string
#      subnet_ip             = string
#      subnet_private_access = optional(string)
#
#    }))
#    firewall_rules = optional(list(object({
#      name        = string
#      description = optional(string)
#      direction   = string
#      priority    = number
#      ranges      = optional(list(string))
#      deny = optional(list(object({
#        protocol = optional(string)
#        ports    = optional(list(string))
#      })))
#      allow = optional(list(object({
#        protocol = optional(string)
#        ports    = optional(list(string))
#      })))
#      target_tags             = optional(list(string))
#      source_tags             = optional(list(string))
#      source_service_accounts = optional(list(string))
#      target_service_accounts = optional(list(string))
#      log_config = object({
#        metadata = string
#      })
#    })))
#  }))
#}
#
#variable "gcv_vpc_configuration" {
#  type = map(object({
#    network_name = string
#  }))
#}
#
#variable "sa_permissions" {
#  type = map(object({
#    project_belong = string
#    account_id     = optional(string)
#    user           = optional(string)
#    roles          = list(string)
#    member         = string
#  }))
#}
#
#variable "peer_config" {
#  type = map(object({
#    local_network              = string
#    peer_network               = string
#    export_local_custom_routes = optional(bool)
#    export_peer_custom_routes  = optional(bool)
#  }))
#}
#
#variable "cloud_nat_configuration" {
#  type = map(object({
#    router_name       = string
#    region            = string
#    router_asn        = number
#    advertise_mode    = optional(string)
#    advertised_groups = optional(list(string))
#    nats              = optional(any)
#  }))
#}
#
## Can't use modules output's to terraform issue in for_each so need to have defined map
#variable "shared_vpc_configuration" {
#  type = object({
#    host_project_name        = string
#    service_project_ids      = string
#    service_project_num      = number
#    host_subnets             = list(string)
#    host_subnet_regions      = list(string)
#    host_subnet_users        = optional(map(any))
#    host_service_agent_role  = optional(bool)
#    host_service_agent_users = optional(list(string))
#  })
#}
#
#variable "vpn_configuration" {
#  type = object({
#    vpn_name                = string
#    project_name            = string
#    tunnel_name_prefix      = optional(string)
#    onprem_ip               = string
#    network_name            = string
#    remote_subnet           = list(string)
#    local_traffic_selector  = optional(list(string))
#    remote_traffic_selector = optional(list(string))
#  })
#}
#
#variable "vpc_private_connections" {
#  type = map(object({
#    range   = string
#    project = string
#  }))
#}
#
#variable "dns_configuration" {
#  type = map(object({
#    type       = string
#    project_id = string
#    domain     = string
#    #visible_network = optional(list(string))
#    labels         = optional(map(any))
#    target_network = optional(string)
#  }))
#}
#
#variable "container_image" {
#  type = object({
#    project        = string
#    name           = string
#    name_sa        = string
#    image          = string
#    metadata       = optional(any)
#    machine_type   = string
#    tag            = string
#    zone           = string
#    restart_policy = string
#    static_ip_name = string
#  })
#}
#
#variable "dns_policy" {
#  type = object({
#    name              = string
#    project           = string
#    enable_forwarding = bool
#    logging           = bool
#  })
#}
#
#variable "cloud_builds" {
#  type = object({
#    project        = string
#    repo_name      = string
#    branch         = string
#    container_name = string
#    tag            = string
#  })
#}
#
#variable "organization_role" {
#  type = map(object({
#    roles = list(string)
#    domain = string
#  }))
#}
