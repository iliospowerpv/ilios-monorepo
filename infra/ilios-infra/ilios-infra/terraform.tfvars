billing_account = "01FF9F-7E0C2A-5E9C35"

organization_id = "9240743021"

region = "us-central1"

#billing_dataset_name = "all_billing_data"
#
#billing_log_sink_name = "billing-bigquery-logsink"

folders = {
  Environments = {
    root_name = "Environments"
    nested_names = [
      "UAT", 
      "Tools",
      "Dev",
      "QA"
    ]
    per_folder_admins = {
      "Management"      = "group:softserveinc@iliospower.com"
      "Global Network"  = "group:softserveinc@iliospower.com"

    }
    all_folder_admins = [
      "group:softserveinc@iliospower.com",
    ]
    folder_admin_roles = [
      "roles/owner",
      "roles/resourcemanager.folderViewer",
      "roles/resourcemanager.projectCreator",
      "roles/compute.networkAdmin"
    ]
  }
}

projects = {
  UAT = {
    project_name      = "prj-uat-base"
    folder_root       = "Environments"
    folder_belong     = "UAT"
    create_project_sa = false
    api_list = [
      "pubsub.googleapis.com",
      "cloudfunctions.googleapis.com",
      "cloudscheduler.googleapis.com",
      "appengine.googleapis.com",
      "sqladmin.googleapis.com",
      "logging.googleapis.com",
      "compute.googleapis.com",
      "iam.googleapis.com",
      "secretmanager.googleapis.com",
      "cloudbuild.googleapis.com",
      "servicenetworking.googleapis.com",
      "cloudresourcemanager.googleapis.com"
    ]
  },
  Tools = {
    project_name      = "prj-monitoring-base"
    folder_root       = "Environments"
    folder_belong     = "Tools"
    create_project_sa = false
    api_list = [
      "pubsub.googleapis.com",
      "cloudfunctions.googleapis.com",
      "cloudscheduler.googleapis.com",
      "appengine.googleapis.com",
      "sqladmin.googleapis.com",
      "logging.googleapis.com",
      "compute.googleapis.com",
      "iam.googleapis.com",
      "secretmanager.googleapis.com",
      "cloudbuild.googleapis.com",
      "servicenetworking.googleapis.com",
      "cloudresourcemanager.googleapis.com",
      "monitoring.googleapis.com"
    ]
  },
  Dev = {
    project_name      = "prj-dev-base"
    folder_root       = "Environments"
    folder_belong     = "Dev"
    create_project_sa = false
    api_list = [
      "pubsub.googleapis.com",
      "cloudfunctions.googleapis.com",
      "cloudscheduler.googleapis.com",
      "appengine.googleapis.com",
      "sqladmin.googleapis.com",
      "logging.googleapis.com",
      "compute.googleapis.com",
      "iam.googleapis.com",
      "secretmanager.googleapis.com",
      "cloudbuild.googleapis.com",
      "servicenetworking.googleapis.com",
      "cloudresourcemanager.googleapis.com"
    ]
  },
  QA = {
    project_name      = "prj-qa-base"
    folder_root       = "Environments"
    folder_belong     = "QA"
    create_project_sa = false
    api_list = [
      "pubsub.googleapis.com",
      "cloudfunctions.googleapis.com",
      "cloudscheduler.googleapis.com",
      "appengine.googleapis.com",
      "sqladmin.googleapis.com",
      "logging.googleapis.com",
      "compute.googleapis.com",
      "iam.googleapis.com",
      "secretmanager.googleapis.com",
      "cloudbuild.googleapis.com",
      "servicenetworking.googleapis.com",
      "cloudresourcemanager.googleapis.com"
    ]
  }
}

audit_conf = {
  project_name         = "prj-audit-p-base"
  location             = "us-central1"
  parent_resource_type = "organization"
  filter               = "" #need later add some filters as a lot of info will be gathered there
  log_sink_name        = "bigquery-audit-logs-sink"
  dataset_name         = "audit_logs"
  auditors_group       = "softserveinc@iliospower.com"
}

#organization_role = {
#  g_gcp_orgadmin = {
#    roles = [
#      "roles/resourcemanager.folderAdmin",
#      "roles/resourcemanager.folderIamAdmin",
#      "roles/resourcemanager.organizationAdmin",
#      "roles/resourcemanager.organizationViewer",
#      "roles/resourcemanager.projectCreator",
#      "roles/resourcemanager.projectDeleter",
#      "roles/resourcemanager.projectIamAdmin",
#      "roles/resourcemanager.projectMover",
#      "roles/billing.user",
#      "roles/vmwareengine.vmwareengineAdmin",
##      "roles/compute.xpnAdmin"
#    ]
#    domain =  "gcp.ilios.com"
#  },
#  g_gcp_billingadmin = {
#    roles  = ["roles/billing.admin"]
#    domain =  "gcp.ilios.com"
#  },
#  g_gcp_networkadmin = {
#    roles = [
#      "roles/compute.networkAdmin",
#      "roles/compute.xpnAdmin",
#      "roles/resourcemanager.folderViewer",
#      "roles/compute.securityAdmin"
#    ]
#    domain =  "gcp.ilios.com"
#  },
#  g_gcp_securityadmin = {
#    roles = [
#      "roles/orgpolicy.policyAdmin",
#      "roles/orgpolicy.policyViewer",
#      "roles/iam.securityReviewer",
#      "roles/resourcemanager.folderIamAdmin",
#      "roles/logging.privateLogViewer",
#      "roles/logging.configWriter",
#      "roles/container.clusterViewer",
#      "roles/bigquery.dataViewer",
#      "roles/compute.orgSecurityPolicyUser"
#    ]
#    domain =  "gcp.ilios.com"
#  },
#  g_gcp_securityviewer = {
#    roles = [
#      "roles/orgpolicy.policyViewer",
#      "roles/iam.securityReviewer",
#      "roles/logging.privateLogViewer",
#      "roles/container.clusterViewer",
#      "roles/bigquery.dataViewer",
#      "roles/compute.orgSecurityPolicyUser",
#      "roles/storage.objectAdmin",
#      "roles/storage.objectViewer"
#    ]
#    domain =  "gcp.ilios.com"
#  },
#  g_gcp_vmadmin = {
#    roles = [
#      "roles/logging.admin",
#      "roles/monitoring.admin",
#      "roles/errorreporting.admin",
#      "roles/servicemanagement.quotaAdmin",
#      "roles/resourcemanager.folderViewer",
#      "roles/compute.admin",
#      "roles/container.admin",
#      "roles/iap.tunnelResourceAccessor",
#      "roles/compute.networkAdmin",
#      "roles/vmwareengine.vmwareengineAdmin",
#      "roles/viewer"
#    ]
#    domain = "gcp.ilios.com"
#  }
#}
#
#vpcs_configuration = {
#  core = {
#    network_name                           = "vpc-p-shared-core-1"
#    shared_vpc_host                        = false
#    routing_mode                           = "REGIONAL"
#    auto_create_subnetworks                = false
#    delete_default_internet_gateway_routes = true
#    mtu                                    = 1460
#    subnets = [
#      {
#        subnet_region         = "europe-west3"
#        subnet_name           = "sb-p-shared-core-eu-west3-net1"
#        subnet_ip             = "10.200.255.0/28"
#        subnet_private_access = true
#      }
#    ]
#    firewall_rules = [
#      {
#        name        = "core-deny-all"
#        description = "Blocks all connections"
#        direction   = "INGRESS"
#        priority    = 1100
#        ranges = [
#          "0.0.0.0/0"
#        ]
#        deny = [
#          {
#            protocol = "all"
#          }
#        ]
#        allow = []
#        log_config = {
#          metadata = "INCLUDE_ALL_METADATA"
#        }
#      },
#      {
#        name      = "core-allow-iap"
#        direction = "INGRESS"
#        priority  = 1000
#        ranges    = ["35.235.240.0/20"]
#        allow = [
#          {
#            protocol = "tcp"
#            ports    = ["22", "3389"]
#          }
#        ]
#        deny = []
#        log_config = {
#          metadata = "INCLUDE_ALL_METADATA"
#        }
#      },
#      {
#        name      = "core-allow-internal"
#        direction = "INGRESS"
#        priority  = 1000
#        ranges = [
#          "10.200.247.0/24",
#          "10.200.248.0/22",
#          "10.200.255.0/28",
#          "10.1.0.0/16",
#          "10.2.0.0/16",
#          "192.168.0.0/16"
#        ]
#        allow = [
#          {
#            protocol = "all"
#          }
#        ]
#        deny = []
#        #source_tags = ["foo"]
#        #target_tags = ["bar"]
#        log_config = {
#          metadata = "INCLUDE_ALL_METADATA"
#        }
#      }
#    ]
#  },
#  distribution = {
#    network_name                           = "vpc-n-shared-gcve"
#    shared_vpc_host                        = true
#    routing_mode                           = "REGIONAL"
#    auto_create_subnetworks                = false
#    delete_default_internet_gateway_routes = true
#    mtu                                    = 1500
#    subnets = [
#      {
#        subnet_region         = "europe-west3"
#        subnet_name           = "sb-n-shared-service-eu-west3-net1"
#        subnet_ip             = "10.200.247.0/24"
#        subnet_private_access = true
#      }
#    ]
#    firewall_rules = [
#      {
#        name        = "distribution-deny-all"
#        description = "Blocks all connections"
#        direction   = "INGRESS"
#        priority    = 1100
#        ranges = [
#          "0.0.0.0/0"
#        ]
#        deny = [
#          {
#            protocol = "all"
#          }
#        ]
#        allow = []
#        log_config = {
#          metadata = "INCLUDE_ALL_METADATA"
#        }
#      },
#      {
#        name      = "ilios-dev-allow-internal"
#        direction = "INGRESS"
#        priority  = 1000
#        ranges = [
#          "10.200.255.0/28",
#          "10.200.248.0/22",
#          "10.200.247.0/24",
#          "10.1.0.0/16",
#          "10.2.0.0/16",
#          "192.168.0.0/16"
#        ]
#        allow = [
#          {
#            protocol = "all"
#          }
#        ]
#        deny = []
#        #source_tags = ["foo"]
#        #target_tags = ["bar"]
#        log_config = {
#          metadata = "INCLUDE_ALL_METADATA"
#        }
#      },
#      {
#        name      = "distribution-allow-iap"
#        direction = "INGRESS"
#        priority  = 1000
#        ranges    = ["35.235.240.0/20"]
#        allow = [
#          {
#            protocol = "tcp"
#            ports    = ["22", "3389"]
#          }
#        ]
#        deny = []
#        log_config = {
#          metadata = "INCLUDE_ALL_METADATA"
#        }
#      },
#      {
#        name      = "distribution-allow-dns"
#        direction = "INGRESS"
#        priority  = 1000
#        ranges    = ["35.199.192.0/19"]
#        allow = [
#          {
#            protocol = "tcp"
#            ports    = ["53"]
#          },
#          {
#            protocol = "udp"
#            ports    = ["53"]
#          }
#        ]
#        deny = []
#        log_config = {
#          metadata = "INCLUDE_ALL_METADATA"
#        }
#      }
#    ]
#  }
#}
#
#gcv_vpc_configuration = {
#  gcve_dev = {
#    network_name = "vpc-n-wmvare-gcve"
#    mtu          = 1500
#  }
#}
#
#sa_permissions = {
#  gcve_dev = {
#    project_belong = "gcve_dev"
#    account_id     = "vmware-sa"
#    roles          = ["roles/vmwareengine.vmwareengineAdmin", "roles/storage.objectAdmin", "roles/storage.admin"]
#    member         = "serviceAccount"
#  }
#  /*
#  core_user = {
#    project_belong = "core"
#    user           = "okulib@softserveinc.com"
#    roles          = ["roles/viewer", "roles/compute.admin", "roles/compute.networkAdmin"]
#    member         = "user"
#  }
#  vm_dnsmasq = {
#    project_belong = "distribution"
#    account_id     = "dnsmasq-sa"
#    roles          = ["roles/storage.objectViewer"]
#    member         = "serviceAccount"
#  }
#}
#
#peer_config = {
#  nonprod-peering = {
#    local_network              = "core"
#    peer_network               = "distribution"
#    export_local_custom_routes = true
#    export_peer_custom_routes  = true
#  }
#}
#
#cloud_nat_configuration = {
#  core = {
#    router_name       = "cr-c-shared-base-eu-west3-cr1"
#    region            = "europe-west3"
#    router_asn        = 65001
#    advertise_mode    = "CUSTOM" # CUSTOM to not allow "DEFAULT"
#    advertised_groups = ["ALL_SUBNETS"]
#    nats = [
#      {
#        name                               = "nat-c-shared-base-eu-west3-cr1"
#        nat_ip_allocate_option             = "AUTO_ONLY"
#        source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
#      }
#    ]
#  }
#}
#
#shared_vpc_configuration = {
#  host_project_name   = "distribution"
#  service_project_num = 1
#  service_project_ids = "gcve_dev"
#
#  host_subnets = [
#    "sb-n-shared-service-eu-west3-net1"
#  ]
#  host_subnet_regions     = ["europe-west3"]
#  host_service_agent_role = false
#  host_subnet_users = {
#    sb-n-shared-service-eu-west3-net1 = "group:g_gcp_vmadmin@gcp.ilios.com"
#  }
#}
#
#vpn_configuration = {
#  remote_subnet           = ["10.1.0.0/16", "10.2.0.0/16", "192.168.0.0/16"]
#  remote_traffic_selector = ["10.1.0.0/16", "10.2.0.0/16", "192.168.0.0/16"]
#  local_traffic_selector  = ["10.200.0.0/16"]
#  vpn_name                = "vpn-onprem-eu-west3"
#  tunnel_name_prefix      = "vpn-tn-manage-onprem"
#  project_name            = "core"
#  onprem_ip               = "91.217.145.35"
#  network_name            = "core"
#}
#
#vpc_private_connections = {
#  gcve-dev-alocated-range = {
#    range   = "172.16.0.0/24"
#    project = "distribution"
#  },
#  gcve-dev-core-range = {
#    range   = "172.16.1.0/24"
#    project = "core"
#  }
#}
#
#container_image = {
#  name           = "vm-dnsmasq"
#  name_sa        = "vm_dnsmasq"
#  image          = "gcr.io/prj-core-n-distribution-acb4/dnsmasq:v.0.7"
#  project        = "distribution"
#  machine_type   = "g1-small"
#  tag            = "dnsmasq-vm"
#  zone           = "europe-west3-a"
#  restart_policy = "Always"
#  static_ip_name = "dnsmasq-internal-address"
#}
#
#dns_policy = {
#  name              = "inbound-forwarding-policy"
#  project           = "core"
#  enable_forwarding = true
#  logging           = false
#}
#
#cloud_builds = {
#  project        = "distribution"
#  repo_name      = "dns-image"
#  branch         = "main"
#  tag            = "latest"
#  container_name = "dnsmasq"
#}

