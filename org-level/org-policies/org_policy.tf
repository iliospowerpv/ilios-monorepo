/**
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

locals {
  organization_id = var.parent_folder != "" ? null : var.org_id
  folder_id       = var.parent_folder != "" ? var.parent_folder : null
  policy_for      = var.parent_folder != "" ? "folder" : "organization"
}


/******************************************
  Compute org policies
*******************************************/

module "org_disable_nested_virtualization" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "false"
  constraint      = "constraints/compute.disableNestedVirtualization"
}

module "org_disable_serial_port_access" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/compute.disableSerialPortAccess"
}

module "org_compute_disable_guest_attributes_access" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/compute.disableGuestAttributesAccess"
}

module "org_vm_external_ip_access" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "true"
  constraint      = "constraints/compute.vmExternalIpAccess"
}

# module "org_skip_default_network" {
#   source          = "../../modules/org_policy"
#   organization_id = local.organization_id
#   folder_id       = local.folder_id
#   policy_for      = local.policy_for
#   policy_type     = "boolean"
#   enforce         = "true"
#   constraint      = "constraints/compute.skipDefaultNetworkCreation"
# }

module "org_shared_vpc_lien_removal" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/compute.restrictXpnProjectLienRemoval"
}

/******************************************
  Cloud SQL
*******************************************/

module "org_cloudsql_external_ip_access" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/sql.restrictPublicIp"
}

/******************************************
  IAM
*******************************************/

# module "org_domain_restricted_sharing" {
#   source           = "../../modules/org_policy/modules/domain_restricted_sharing"
#   organization_id  = local.organization_id
#   folder_id        = local.folder_id
#   policy_for       = local.policy_for
#   domains_to_allow = var.domains_to_allow
# }

module "org_disable_sa_key_creation" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "false"
  constraint      = "constraints/iam.disableServiceAccountKeyCreation"
}

/******************************************
  Storage
*******************************************/

module "org_enforce_bucket_level_access" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/storage.uniformBucketLevelAccess"
}


module "org_enforce_aim_allowServiceAccountCredentialLifetimeExtension" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "true"
  constraint      = "constraints/iam.allowServiceAccountCredentialLifetimeExtension"
}

module "org_enforce_aim_workloadIdentityPoolAwsAccounts" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "true"
  constraint      = "constraints/iam.workloadIdentityPoolAwsAccounts"
}

module "org_enforce_run_allowedBinaryAuthorizationPolicies" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "false"
  constraint      = "constraints/run.allowedBinaryAuthorizationPolicies"
}

module "org_enforce_resourcemanager_allowedExportDestinations" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "true"
  constraint      = "constraints/resourcemanager.allowedExportDestinations"
}

module "constraints_cloudfunctions_allowedIngressSettings" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "true"
  constraint      = "constraints/cloudfunctions.allowedIngressSettings"
}

module "constraints_run_allowedIngress" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "true"
  constraint      = "constraints/run.allowedIngress"
}

module "constraints_cloudbuild_allowedIntegrations" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "false"
  constraint      = "constraints/cloudbuild.allowedIntegrations"
}

module "constraints_resourcemanager_allowedImportSources" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "true"
  constraint      = "constraints/resourcemanager.allowedImportSources"
}

module "constraints_cloudfunctions_allowedVpcConnectorEgressSettings" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "true"
  constraint      = "constraints/cloudfunctions.allowedVpcConnectorEgressSettings"
}

module "constraints_run_allowedVPCEgress" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "true"
  constraint      = "constraints/run.allowedVPCEgress"
}

module "constraints_meshconfig_allowedVpcscModes" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "true"
  constraint      = "constraints/meshconfig.allowedVpcscModes"
}

module "constraints_cloudbuild_allowedWorkerPools" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "false"
  constraint      = "constraints/cloudbuild.allowedWorkerPools"
}

module "constraints_storage_restrictAuthTypes" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "false"
  constraint      = "constraints/storage.restrictAuthTypes"
}

module "constraints_compute_storageResourceUseRestrictions" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "false"
  constraint      = "constraints/compute.storageResourceUseRestrictions"
}

module "constraints_datastream_disablePublicConnectivity" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/datastream.disablePublicConnectivity"
}

module "constraints_compute_vmExternalIpAccess" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "true"
  constraint      = "constraints/compute.vmExternalIpAccess"
}


module "constraints_compute_disableAllIpv6" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/compute.disableAllIpv6"
}

module "constraints_iam_disableAuditLoggingExemption" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/iam.disableAuditLoggingExemption"
}

module "constraints_bigquery_disableBQOmniAWS" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/bigquery.disableBQOmniAWS"
}

module "constraints_bigquery_disableBQOmniAzure" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/bigquery.disableBQOmniAzure"
}

module "constraints_clouddeploy_disableServiceLabelGeneration" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "false"
  constraint      = "constraints/clouddeploy.disableServiceLabelGeneration"
}

module "constraints_gcp_disableCloudLogging" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "false"
  constraint      = "constraints/gcp.disableCloudLogging"
}

module "constraints_compute_disableGlobalSelfManagedSslCertificate" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/compute.disableGlobalSelfManagedSslCertificate"
}

module "constraints_iap_requireGlobalIapWebDisabled" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/iap.requireGlobalIapWebDisabled"
}

module "constraints_iap_requireRegionalIapWebDisabled" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/iap.requireRegionalIapWebDisabled"
}

module "constraints_compute_disableGlobalLoadBalancing" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "false"
  constraint      = "constraints/compute.disableGlobalLoadBalancing"
}

module "constraints_compute_disableHybridCloudIpv6" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/compute.disableHybridCloudIpv6"
}

module "constraints_compute_disableInternetNetworkEndpointGroup" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/compute.disableInternetNetworkEndpointGroup"
}

module "constraints_compute_disablePrivateServiceConnectCreationForConsumers" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "true"
  constraint      = "constraints/compute.disablePrivateServiceConnectCreationForConsumers"
}

module "constraints_appengine_disableCodeDownload" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "false"
  constraint      = "constraints/appengine.disableCodeDownload"
}

module "constraints_compute_disableSshInBrowser" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "false"
  constraint      = "constraints/compute.disableSshInBrowser"
}

module "constraints_compute_disableSerialPortLogging" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "false"
  constraint      = "constraints/compute.disableSerialPortLogging"
}

module "constraints_compute_disableVpcExternalIpv6" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/compute.disableVpcExternalIpv6"
}

module "constraints_compute_disableVpcInternalIpv6" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/compute.disableVpcInternalIpv6"
}

module "constraints_iam_disableWorkloadIdentityClusterCreation" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/iam.disableWorkloadIdentityClusterCreation"
}

module "constraints_storage_publicAccessPrevention" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/storage.publicAccessPrevention"
}

module "constraints_gcp_detailedAuditLoggingMode" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/gcp.detailedAuditLoggingMode"
}


module "constraints_gcp_resourceLocations" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = false
  allow         = ["europe-west2", "europe-west3"]
  constraint      = "constraints/gcp.resourceLocations"
}

module "constraints_resourcemanager_allowEnabledServicesForExport" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "true"
  constraint      = "constraints/resourcemanager.allowEnabledServicesForExport"
}

module "constraints_firestore_requireP4SAforImportExport" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "false"
  constraint      = "constraints/firestore.requireP4SAforImportExport"
}

module "constraints_compute_requireOsLogin" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "false"
  constraint      = "constraints/compute.requireOsLogin"
}

# module "constraints_compute_requireVpcFlowLogs" {
#   source          = "../../modules/org_policy"
#   organization_id = local.organization_id
#   folder_id       = local.folder_id
#   policy_for      = local.policy_for
#   policy_type     = "list"
#   enforce         = "false"
#   constraint      = "constraints/compute.requireVpcFlowLogs"
# }

module "constraints_cloudfunctions_requireVPCConnector" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "false"
  constraint      = "constraints/cloudfunctions.requireVPCConnector"
}

module "constraints_sql_restrictAuthorizedNetworks" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/sql.restrictAuthorizedNetworks"
}

module "constraints_compute_restrictCloudNATUsage" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "true"
  constraint      = "constraints/compute.restrictCloudNATUsage"
}

module "constraints_compute_restrictDedicatedInterconnectUsage" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "true"
  constraint      = "constraints/compute.restrictDedicatedInterconnectUsage"
}

module "constraints_compute_restrictLoadBalancerCreationForTypes" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  allow           = ["INTERNAL_TCP_UDP", "GLOBAL_EXTERNAL_MANAGED_HTTP_HTTPS"]
  constraint      = "constraints/compute.restrictLoadBalancerCreationForTypes"
}

module "constraints_compute_restrictNonConfidentialComputing" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "false"
  constraint      = "constraints/compute.restrictNonConfidentialComputing"
}

module "constraints_compute_restrictPartnerInterconnectUsage" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "true"
  constraint      = "constraints/compute.restrictPartnerInterconnectUsage"
}

module "constraints_compute_restrictProtocolForwardingCreationForTypes" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "false"
  constraint      = "constraints/compute.restrictProtocolForwardingCreationForTypes"
}

module "constraints_iam_restrictCrossProjectServiceAccountLienRemoval" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "false"
  constraint      = "constraints/iam.restrictCrossProjectServiceAccountLienRemoval"
}

module "constraints_resourcemanager_accessBoundaries" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "false"
  constraint      = "constraints/resourcemanager.accessBoundaries"
}

module "constraints_compute_restrictSharedVpcHostProjects" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "true"
  constraint      = "constraints/compute.restrictSharedVpcHostProjects"
}

module "constraints_compute_vmCanIpForward" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "true"
  constraint      = "constraints/compute.vmCanIpForward"
}

module "constraints_compute_restrictVpcPeering" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "false"
  constraint      = "constraints/compute.restrictVpcPeering"
}

module "constraints_cloudkms_allowedProtectionLevels" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "false"
  constraint      = "constraints/cloudkms.allowedProtectionLevels"
}

module "constraints_gcp_restrictCmekCryptoKeyProjects" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "false"
  constraint      = "constraints/gcp.restrictCmekCryptoKeyProjects"
}

module "constraints_gcp_restrictNonCmekServices" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "false"
  constraint      = "constraints/gcp.restrictNonCmekServices"
}

module "constraints_storage_retentionPolicySeconds" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "false"
  constraint      = "constraints/storage.retentionPolicySeconds"
}

module "constraints_compute_setNewProjectDefaultToZonalDNSOnly" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "false"
  constraint      = "constraints/compute.setNewProjectDefaultToZonalDNSOnly"
}

module "constraints_compute_sharedReservationsOwnerProjects" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "list"
  enforce         = "true"
  constraint      = "constraints/compute.sharedReservationsOwnerProjects"
}

module "constraints_compute_requireShieldedVm" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/compute.requireShieldedVm"
}

module "constraints_compute_skipDefaultNetworkCreation" {
  source          = "../../modules/org_policy"
  organization_id = local.organization_id
  folder_id       = local.folder_id
  policy_for      = local.policy_for
  policy_type     = "boolean"
  enforce         = "true"
  constraint      = "constraints/compute.skipDefaultNetworkCreation"
}




# /******************************************
#   Access Context Manager Policy
# *******************************************/

# resource "google_access_context_manager_access_policy" "access_policy" {
#   count  = var.create_access_context_manager_access_policy ? 1 : 0
#   parent = "organizations/${var.org_id}"
#   title  = "default policy"
# }
