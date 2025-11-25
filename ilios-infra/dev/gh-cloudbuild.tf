// Create a secret containing the personal access token and grant permissions to the Service Agent
resource "google_secret_manager_secret" "github_token_secret" {
    project =  "prj-dev-base-e61d"
    secret_id = "GH-Token"

    replication {
        auto {}
    }
}

# resource "google_secret_manager_secret_version" "github_token_secret_version" {
#     secret = google_secret_manager_secret.github_token_secret.id
#     secret_data = "Ilios"
# }

data "google_iam_policy" "serviceagent_secretAccessor" {
    binding {
        role = "roles/secretmanager.secretAccessor"
        members = ["serviceAccount:cloud-build-cust-svc-acct@prj-dev-base-e61d.iam.gserviceaccount.com"]
    }
}

resource "google_secret_manager_secret_iam_policy" "policy" {
  project = google_secret_manager_secret.github_token_secret.project
  secret_id = google_secret_manager_secret.github_token_secret.secret_id
  policy_data = data.google_iam_policy.serviceagent_secretAccessor.policy_data
}

// Create the GitHub connection
resource "google_cloudbuildv2_connection" "my_connection" {
    project = "prj-dev-base-e61d"
    location = "us-west1"
    name = "ilios2"

    github_config {
        app_installation_id = "47572502"
        authorizer_credential {
            oauth_token_secret_version = "projects/720699231124/secrets/GH-Token/versions/2"
        }
    }
    depends_on = [google_secret_manager_secret_iam_policy.policy]
}