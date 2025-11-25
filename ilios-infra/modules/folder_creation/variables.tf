variable "root_folder" {
  description = "The folder’s display name"
}
variable "parent_id" {
  description = "The resource name of the parent Folder or Organization"
}
variable "nested_folder" {
  type        = list(any)
  description = "The nested folder’s display name"
}

variable "folder_admin_roles" {}

variable "per_folder_admins" {}

variable "all_folder_admins" {}