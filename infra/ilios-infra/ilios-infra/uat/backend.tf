terraform {
  backend "gcs" {
    bucket      = "cft-tfstate-0f9a"
    prefix      = "terraform/terraform-uat.tfstate"
  }
}

#terraform {
#  backend "local" {
#    path = "./terraform-folders.tfstate"
#  }
#}