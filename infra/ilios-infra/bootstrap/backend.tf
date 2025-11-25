#terraform {
#  backend "gcs" {
#    credentials = "../prj-admin-base-bbd5-c3fb785deaae.json"
#    bucket      = "cft-tfstate-f5ab"
#    prefix      = "terraform/terraform-bootstrap.tfstate"
#  }
#}

terraform {
  backend "gcs" {
#    credentials = "../prj-admin-base-bbd5-c3fb785deaae.json"
    bucket      = "cft-tfstate-0f9a"
    prefix      = "terraform/terraform-bootstrap.tfstate"
  }
}

#terraform {
#  backend "local" {
#    path = "./terraform-bootstrap.tfstate"
#  }
#}
