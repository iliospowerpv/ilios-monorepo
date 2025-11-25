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


org_id = "9240743021"

billing_account = "01FF9F-7E0C2A-5E9C35"


#terraform_service_account_org_admin = "management-terraform@management-terraform.iam.gserviceaccount.com"

default_region = "us-central1"


//Optional - for development.  Will place all resources under a specific folder instead of org root
//parent_folder = "01234567890"
//scc_notification_filter = "state=\\\"ACTIVE\\\""




group_email = [
]


permissions_billing_admins = "roles/billing.admin"

permissions_billing_viewers = [
    #change_billing_viewers
    "roles/billing.viewer"
]

permissions_org_admins = [
    #chnage_org_admins
    "roles/resourcemanager.folderAdmin",
    "roles/resourcemanager.folderIamAdmin",
    "roles/resourcemanager.organizationAdmin",
    "roles/resourcemanager.organizationViewer",
    "roles/resourcemanager.projectCreator",
    "roles/resourcemanager.projectDeleter",
    "roles/resourcemanager.projectIamAdmin",
    "roles/resourcemanager.projectMover",
    "roles/billing.user",
    "roles/owner",
    "roles/orgpolicy.policyAdmin",
    "roles/iam.organizationRoleAdmin",
    "roles/cloudsupport.admin"
]

permissions_folder_admins = [
    #change_folder_admins
    "roles/resourcemanager.folderAdmin",
    "roles/resourcemanager.folderIamAdmin",
    "roles/resourcemanager.projectCreator",
    "roles/resourcemanager.projectDeleter",
    "roles/resourcemanager.projectIamAdmin",
    "roles/resourcemanager.projectMover"
]

permissions_project_admins = [
    #change_project_admins
    # "roles/resourcemanager.projectCreator",
    # "roles/resourcemanager.projectDeleter",
    # "roles/resourcemanager.projectIamAdmin",
    # "roles/resourcemanager.projectMover",
    "roles/editor",
    "roles/iap.tunnelResourceAccessor"
]

permissions_project_nonprod_admins = [
    #change_project_nonprod_admins
    # "roles/resourcemanager.projectCreator",
    # "roles/resourcemanager.projectDeleter",
    # "roles/resourcemanager.projectIamAdmin",
    # "roles/resourcemanager.projectMover",
    "roles/editor",
    "roles/iap.tunnelResourceAccessor"
]



permissions_network_admins = [
    #chnage_network_admins
    "roles/compute.networkAdmin",
    "roles/compute.xpnAdmin",
    "roles/resourcemanager.folderViewer",
    "roles/compute.securityAdmin"
]

permissions_network_nonprod_admins = [
    #change_network_nonprod_admins
    "roles/compute.networkAdmin",
    "roles/compute.xpnAdmin",
    "roles/resourcemanager.folderViewer",
    "roles/compute.securityAdmin"
]

permissions_security_admins = [
    #change_security_admins
    "roles/orgpolicy.policyAdmin",
    "roles/orgpolicy.policyViewer",
    "roles/iam.securityReviewer",
    "roles/resourcemanager.folderIamAdmin",
    "roles/logging.privateLogViewer",
    "roles/logging.configWriter",
    "roles/container.clusterViewer",
    "roles/bigquery.dataViewer",
    "roles/compute.orgSecurityPolicyUser",
    "roles/securitycenter.admin",
    "roles/logging.admin"
]

permissions_developers = [
    #change_developers
    "roles/compute.networkViewer",
    "roles/compute.osLogin",
    "roles/compute.viewer",
    "roles/monitoring.viewer",
    "roles/logging.admin"
]

permissions_nonprod_developers = [
    #change_nonprod_developers
     "roles/compute.networkViewer",
    "roles/compute.osLogin",
    "roles/compute.viewer",
    "roles/monitoring.viewer",
    "roles/logging.admin"
]

permissions_lead_developers = [
    #chnage_lead_developers
    "roles/compute.admin",
    "roles/container.admin"
]

permissions_org_viewers = [
    #change_org_viewers  
    "roles/resourcemanager.organizationViewer",
    "roles/viewer",
    "roles/cloudasset.viewer",
    "roles/browser"
]

permissions_org_browsers = [
    #change_org_browsers
    "roles/browser"
]

permissions_folder_viewers = [
    #chnage_folder_viewers
    "roles/resourcemanager.folderViewer"
]

permissions_project_viewers = [
    #change_project_viewers
    "roles/viewer",
    "roles/iap.tunnelResourceAccessor",
    "roles/browser",
    "roles/compute.osAdminLogin",
    "roles/iam.serviceAccountUser"
]

permissions_project_owner = [
    #change_project_viewers
    "roles/owner",
    "roles/iap.tunnelResourceAccessor"
]