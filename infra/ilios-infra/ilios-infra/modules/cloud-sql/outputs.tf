output "instances" {
  value = {
    for instance_key, instance in google_sql_database_instance.master_instance :
    instance_key => instance
  }
}

output "secrets" {
  value = {
    for secret_key, secret in google_secret_manager_secret.db_user_password :
    secret_key => secret
  }
}
