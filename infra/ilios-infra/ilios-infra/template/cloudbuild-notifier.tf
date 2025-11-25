## Project

data "google_project" "cloudbuild_notifier_project" {
  project_id = var.project_id
}

## IAM

resource "google_service_account" "cloudbuild_notifier_account" {
  project      = var.project_id
  account_id   = "cloudbuild-notifier"
  description  = "Service account for Cloud Build notifications daemon"
}

resource "google_service_account" "cloudbuild_notifier_trigger_account" {
  project      = var.project_id
  account_id   = "cloudbuild-notifier-invoker"
  description  = "Service account for Cloud Build notifications daemon triggering"
}

## Secret Manager

resource "google_secret_manager_secret_iam_member" "cloudbuild_notifier_secrets_access" {
  project   = var.project_id
  secret_id = "cloudbuild-notifier-smtp-creds"
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloudbuild_notifier_account.email}"
}

## Storage

resource "google_storage_bucket" "cloudbuild_notifier_configuration_bucket" {
  name     = "ilios-cloudbuild-notifiers-${var.environment}"
  location = var.region
  project  = var.project_id
}

resource "google_storage_bucket_object" "cloudbuild_notifier_configuration" {
  name    = "smtp/config.yaml"
  bucket  = google_storage_bucket.cloudbuild_notifier_configuration_bucket.name
  content = <<EOF
apiVersion: cloud-build-notifiers/v1
kind: SMTPNotifier
metadata:
  name: cloudbuild-smtp-notifier
spec:
  notification:
    filter: build.status in [Build.Status.SUCCESS, Build.Status.FAILURE, Build.Status.TIMEOUT] && "TRIGGER_NAME" in build.substitutions
    delivery:
      server: smtp.mailgun.org
      port: '587'
      subject: 'Cloud Build [{{.Build.Substitutions.PROJECT_ID}}] - {{ if eq .Build.Status 3 }}SUCCESS{{ else }}FAILED{{ end }}'
      sender: cloudbuild@iliospower.com
      from: cloudbuild@iliospower.com
      recipients:
      - 0efa879c.softserveinc.onmicrosoft.com@emea.teams.ms
      password:
        secretRef: smtp-password
    template:
      type: golang
      uri: gs://${google_storage_bucket.cloudbuild_notifier_configuration_bucket.name}/${google_storage_bucket_object.cloudbuild_notifier_template.name}
  secrets:
  - name: smtp-password
    value: projects/${data.google_project.cloudbuild_notifier_project.number}/secrets/cloudbuild-notifier-smtp-creds/versions/latest
EOF
}

resource "google_storage_bucket_object" "cloudbuild_notifier_template" {
  name    = "smtp/template.tpl"
  bucket  = google_storage_bucket.cloudbuild_notifier_configuration_bucket.name
  content = <<EOF
<html>
  <body>
    {{ if eq .Build.Status 3 }}&#9989;{{ else }}&#10060;{{ end }} Pipeline for <b>{{.Build.Substitutions.TRIGGER_NAME}}</b> was {{ if eq .Build.Status 3 }}completed successfully{{ else }}failed{{ end }}!<br />
    &#128195; <a href="{{.Build.LogUrl}}">Open Build Logs</a>
  </body>
</html>
EOF
}

resource "google_storage_bucket_iam_member" "cloudbuild_notifier_configuration_access" {
  bucket = google_storage_bucket.cloudbuild_notifier_configuration_bucket.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.cloudbuild_notifier_account.email}"
}

## Cloud Run

resource "google_cloud_run_v2_service" "cloudbuild_notifier_service" {
  name     = "cloudbuild-notifier"
  location = var.region
  project  = var.project_id
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    timeout = "300s"
    max_instance_request_concurrency = 20
    service_account = google_service_account.cloudbuild_notifier_account.email

    scaling {
      max_instance_count = 1
    }
    containers {
      name = "smtp"
      image = "us-east1-docker.pkg.dev/gcb-release/cloud-build-notifiers/smtp:latest"
      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "CONFIG_PATH"
        value = "gs://${google_storage_bucket.cloudbuild_notifier_configuration_bucket.name}/${google_storage_bucket_object.cloudbuild_notifier_configuration.name}"
      }
      ports {
        container_port = 8080
      }
      resources {
        limits = {
          "cpu" = "1000m"
          "memory" = "256Mi"
        }
        startup_cpu_boost = true
        cpu_idle = true
      }
    }
  }
  traffic {
    type = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
  depends_on = [
    google_secret_manager_secret_iam_member.cloudbuild_notifier_secrets_access
  ]
}

resource "google_cloud_run_v2_service_iam_member" "cloudbuild_notifier_service_access" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.cloudbuild_notifier_service.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.cloudbuild_notifier_trigger_account.email}"
}

## Pub/Sub

resource "google_project_iam_member" "pubsub_access" {
  project = var.project_id
  role    = "roles/iam.serviceAccountTokenCreator"
  member  = "serviceAccount:service-${data.google_project.cloudbuild_notifier_project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_topic" "cloudbuild_topic" {
  name     = "cloud-builds"
  project  = var.project_id
}

resource "google_pubsub_subscription" "cloudbuild_subscription" {
  name                 = "cloudbuild-notifier"
  project              = var.project_id
  topic                = google_pubsub_topic.cloudbuild_topic.id
  ack_deadline_seconds = 60
  push_config {
    push_endpoint = google_cloud_run_v2_service.cloudbuild_notifier_service.uri
    oidc_token {
      service_account_email = google_service_account.cloudbuild_notifier_trigger_account.email
    }
  }
}