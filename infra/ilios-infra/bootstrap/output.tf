output "bucket" {
  value = module.bootstrap.gcs_bucket_tfstate
}

output "project_id" {
  value = module.bootstrap.seed_project_id
}

output "terraform_sa_email" {
  value = module.bootstrap.terraform_sa_email
}

output "terraform_sa_name" {
  value = module.bootstrap.terraform_sa_name
}