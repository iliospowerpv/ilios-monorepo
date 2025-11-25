// Create a secret containing the personal access token and grant permissions to the Service Agent
resource "google_secret_manager_secret" "github_token_secret" {
    project =  var.project_id
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
        #members = ["serviceAccount:cloud-build-cust-svc-acct@prj-dev-base-e61d.iam.gserviceaccount.com"]
        members = ["serviceAccount:${google_service_account.cloud_build_sa.email}"]
    }
    depends_on = [google_service_account.cloud_build_sa]
}

resource "google_secret_manager_secret_iam_policy" "policy" {
  project = google_secret_manager_secret.github_token_secret.project
  secret_id = google_secret_manager_secret.github_token_secret.secret_id
  policy_data = data.google_iam_policy.serviceagent_secretAccessor.policy_data
}

// Create the GitHub connection
resource "google_cloudbuildv2_connection" "my_connection" {
    project = var.project_id
    location = var.region
    name = "ilios2"

    github_config {
        app_installation_id = "47572502"
        authorizer_credential {
            oauth_token_secret_version = "projects/${var.project_id}/secrets/GH-Token/versions/latest"
        }
    }
    depends_on = [google_secret_manager_secret_iam_policy.policy]
}


// Cloud Build WorkerPool
resource "google_cloudbuild_worker_pool" "pool" {
  project = var.project_id
  name = "privat-pool"
  location = var.region
  worker_config {
    disk_size_gb = 100
    machine_type = "e2-standard-4"
    no_external_ip = false
  }
  network_config {
    peered_network = google_compute_network.default.id
  }
  depends_on = [google_compute_network.default]
}


// FrontEnd
resource "google_cloudbuildv2_repository" "frontend" {
  project = var.project_id
  name = "rea-investment-fe"
  parent_connection = google_cloudbuildv2_connection.my_connection.id
  remote_uri = "https://github.com/GH-50513/rea-investment-fe.git"
  depends_on = [google_cloudbuildv2_connection.my_connection]
}

resource "google_cloudbuild_trigger" "frontend-trigger" {
  project = var.project_id
  location = var.region
  name     = "frontend"

  source_to_build {
    repository = google_cloudbuildv2_repository.frontend.id
    ref        = "refs/heads/main"
    repo_type  = "GITHUB"
  }

  git_file_source {
    repository = google_cloudbuildv2_repository.frontend.id
    revision   = "refs/heads/main"
    repo_type  = "GITHUB"
    path       = "cloudbuild.yaml"
  }
  
  substitutions = {
    _ENVIRONMENT = "${var.environment}"
  }
}

// BackEnd
resource "google_cloudbuildv2_repository" "backend" {
  project = var.project_id
  name = "ilios-server"
  parent_connection = google_cloudbuildv2_connection.my_connection.id
  remote_uri = "https://github.com/GH-50513/ilios-server.git"
  depends_on = [google_cloudbuildv2_connection.my_connection]
}

resource "google_cloudbuild_trigger" "backend-trigger" {
  project = var.project_id
  location = var.region
  name = "backend"

  source_to_build {
    repository = google_cloudbuildv2_repository.backend.id
    ref        = "refs/heads/main"
    repo_type  = "GITHUB"
  }

  git_file_source {
    repository = google_cloudbuildv2_repository.backend.id
    revision   = "refs/heads/main"
    repo_type  = "GITHUB"
    path       = "cloudbuild.yaml"
  }

  substitutions = {
    _ENVIRONMENT = "${var.environment}"
  }
}

resource "google_cloudbuild_trigger" "backend-downgrade-trigger" {
  project = var.project_id
  location = var.region
  name = "backend-downgrade"
  service_account = "projects/${var.project_id}/serviceAccounts/${var.project_id}@appspot.gserviceaccount.com"

  source_to_build {
    repository = google_cloudbuildv2_repository.backend.id
    ref        = "refs/heads/main"
    repo_type  = "GITHUB"
  }

  git_file_source {
    repository = google_cloudbuildv2_repository.backend.id
    revision   = "refs/heads/main"
    repo_type  = "GITHUB"
    path       = "cloudbuild_downgrade.yaml"
  }

  substitutions = {
    _ENVIRONMENT = "${var.environment}"
    _ALEMBIC_REF = ""
    _GIT_REF     = ""
  }
}

// Backend services
resource "google_cloudbuildv2_repository" "backend-services" {
  project = var.project_id
  name = "ilios-services"
  parent_connection = google_cloudbuildv2_connection.my_connection.id
  remote_uri = "https://github.com/GH-50513/ilios-services.git"
  depends_on = [google_cloudbuildv2_connection.my_connection]
}

resource "google_cloudbuild_trigger" "backend-sites-weather" {
  project = var.project_id
  location = var.region
  name = "fetch-sites-weather"
  service_account = "projects/${var.project_id}/serviceAccounts/${var.project_id}@appspot.gserviceaccount.com"

  repository_event_config {
    repository = google_cloudbuildv2_repository.backend-services.id
    push {
      branch = "main"
    }
  }

  filename = "services/fetch_sites_weather/cloudbuild.yaml"
}

resource "google_cloud_scheduler_job" "backend-sites-weather-trigger" {
  project          = var.project_id
  region           = var.region
  name             = "fetch-sites-weather-trigger"
  schedule         = "0 * * * *"
  time_zone        = "America/New_York"
  attempt_deadline = "60s"

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-${var.project_id}.cloudfunctions.net/fetch_sites_weather"

    oidc_token {
      service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
    }
  }
}

// AI Integration
resource "google_cloudbuildv2_repository" "integration_ai" {
  project = var.project_id
  name = "ilios-DocAI"
  parent_connection = google_cloudbuildv2_connection.my_connection.id
  remote_uri = "https://github.com/GH-50513/ilios-DocAI.git"
  depends_on = [google_cloudbuildv2_connection.my_connection]
}

resource "google_cloudbuild_trigger" "integration_ai_job_trigger" {
  project = var.project_id
  location = var.region
  name = "integration-ai-job"
  service_account = "projects/${var.project_id}/serviceAccounts/${var.project_id}@appspot.gserviceaccount.com"
  included_files = ["src/**"]

  repository_event_config {
    repository = google_cloudbuildv2_repository.integration_ai.id
    push {
      branch = "^main$"
    }
  }

  substitutions = {
    _ENV = "${upper(var.environment)}"
    _BACKEND_URL = "https://backend-dot-${var.project_id}.uc.r.appspot.com/api/internal/files/{file_id}/parsing"
  }

  filename = "src/deployment/cloud_run_job/cloudbuild.yaml"
}

resource "google_cloudbuild_trigger" "integration_ai_function_trigger" {
  project = var.project_id
  location = var.region
  name = "integration-ai-function"
  service_account = "projects/${var.project_id}/serviceAccounts/${var.project_id}@appspot.gserviceaccount.com"
  included_files = ["src/deployment/cloud_function/**"]

  repository_event_config {
    repository = google_cloudbuildv2_repository.integration_ai.id
    push {
      branch = "^main$"
    }
  }

  filename = "src/deployment/cloud_function/cloudbuild.yaml"
}

// Co-terminus
resource "google_cloudbuild_trigger" "co-terminus_trigger" {
  project = var.project_id
  location = var.region
  name = "co-terminus"
  service_account = "projects/${var.project_id}/serviceAccounts/${var.project_id}@appspot.gserviceaccount.com"
  included_files = ["src/**"]

  repository_event_config {
    repository = google_cloudbuildv2_repository.integration_ai.id
    push {
      branch = "^main$"
    }
  }

  substitutions = {
    _ENV = "${upper(var.environment)}"
    _ENVIRONMENT = var.environment
    _BACKEND_URL = "https://backend-dot-${var.project_id}.uc.r.appspot.com/api/internal/co-terminus-checks/{record_id}/results"
  }

  filename = "src/deployment/fast_api/cloudbuild.yaml"
}