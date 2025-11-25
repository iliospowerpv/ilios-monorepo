resource "google_folder" "root-folder" {
  display_name = var.root_folder
  parent       = var.parent_id
}

# Folder nested under another folder.r
module "folders" {
  source  = "terraform-google-modules/folders/google"
  version = "~> 3.0"

  parent = google_folder.root-folder.name

  names = var.nested_folder

  set_roles = true

  per_folder_admins = var.per_folder_admins

  all_folder_admins = var.all_folder_admins
}
