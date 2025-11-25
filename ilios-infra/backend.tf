terraform {
  backend "gcs" {
    #credentials = "/Users/nkondra/Desktop/ilios/prj-admin-p-base-a82f-1bf0a233a1cb.json"
    bucket      = "cft-tfstate-0f9a"
    prefix      = "terraform/terraform-folders.tfstate"
  }
}

#terraform {
#  backend "local" {
#    path = "./terraform-folders.tfstate"
#  }
#}