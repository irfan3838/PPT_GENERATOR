# ─── Service Account: Cloud Run runtime ─────────────────────────────────────

resource "google_service_account" "cloud_run_sa" {
  account_id   = "ppt-builder-runtime"
  display_name = "PPT Builder – Cloud Run Runtime SA"
  description  = "Used by the Cloud Run service to access GCS and Secret Manager"
}

# Read/write generated artifacts to GCS
resource "google_storage_bucket_iam_member" "cloud_run_sa_gcs" {
  bucket = google_storage_bucket.artifacts.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Access application secrets from Secret Manager
resource "google_project_iam_member" "cloud_run_sa_secrets" {
  project = var.gcp_project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Write structured logs to Cloud Logging
resource "google_project_iam_member" "cloud_run_sa_logging" {
  project = var.gcp_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# ─── Service Account: GitHub Actions deployment ──────────────────────────────

resource "google_service_account" "github_actions_sa" {
  account_id   = "ppt-builder-github-actions"
  display_name = "PPT Builder – GitHub Actions Deployment SA"
  description  = "Impersonated by GitHub Actions via Workload Identity to deploy"
}

# Deploy Cloud Run revisions
resource "google_project_iam_member" "github_actions_run_admin" {
  project = var.gcp_project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.github_actions_sa.email}"
}

# Push Docker images to Artifact Registry
resource "google_project_iam_member" "github_actions_ar_writer" {
  project = var.gcp_project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.github_actions_sa.email}"
}

# Allow GitHub Actions SA to act as the Cloud Run SA when deploying
resource "google_service_account_iam_member" "github_actions_impersonate_run_sa" {
  service_account_id = google_service_account.cloud_run_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github_actions_sa.email}"
}
