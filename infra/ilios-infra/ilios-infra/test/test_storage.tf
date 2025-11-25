#module "gcs_buckets" {
#  source  = "terraform-google-modules/cloud-storage/google"
#  version = "~> 5.0"
#  project_id  = "<PROJECT ID>"
#  names = ["first"]
##  names = ["first", "second"]
#  prefix = "my-unique-prefix"
#  set_admin_roles = true
#  admins = ["group:foo-admins@example.com"]
#  versioning = {
#    first = true
#  }
#  bucket_admins = {
#    second = "user:spam@example.com,user:eggs@example.com"
#  }
#}


#module "gcs_buckets" {
#  source  = "terraform-google-modules/cloud-storage/google"
#  version = "~> 5.0"
#  project_id  = module.project_creation["Dev"].project_ids.project_id
#  location = "us-west1"
#  names = ["first325978"]
##  names = ["first", "second"]
#  prefix = "ilios"
#  set_admin_roles = true
#  admins = ["group:softserveinc@iliospower.com"]
#  versioning = {
#    first325978 = true
#  }
##  bucket_admins = {
##    second = "user:spam@example.com,user:eggs@example.com"
##  }
#  force_destroy = {
#    first325978 = true
#  }
#}