# ─── Cloud Run: Streamlit application ────────────────────────────────────────

locals {
  image_url = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/ppt-builder/app:latest"

  # Map secret IDs to env var names for Cloud Run
  secret_env_vars = {
    GEMINI_API_KEY      = "ppt-builder-gemini-api-key"
    NANO_BANANA_API_KEY = "ppt-builder-nano-banana-api-key"
    GMAIL_SENDER_EMAIL  = "ppt-builder-gmail-email"
    GMAIL_SENDER_PASSWORD = "ppt-builder-gmail-password"
  }
}

resource "google_cloud_run_v2_service" "ppt_builder" {
  name     = "ppt-builder"
  location = var.gcp_region

  deletion_protection = false

  template {
    service_account = google_service_account.cloud_run_sa.email

    scaling {
      min_instance_count = var.cloud_run_min_instances
      max_instance_count = var.cloud_run_max_instances
    }

    containers {
      image = local.image_url

      resources {
        limits = {
          memory = "2Gi"
          cpu    = "2"
        }
        # CPU only allocated during request processing (cost saving)
        cpu_idle = false
        startup_cpu_boost = true
      }

      ports {
        container_port = 8501
      }

      # ── Plain environment variables ────────────────────────────────────────
      env {
        name  = "GCP_PROJECT_ID"
        value = var.gcp_project_id
      }
      env {
        name  = "GCP_BUCKET_NAME"
        value = google_storage_bucket.artifacts.name
      }
      env {
        name  = "GEMINI_FLASH_MODEL"
        value = var.gemini_flash_model
      }
      env {
        name  = "GEMINI_PRO_MODEL"
        value = var.gemini_pro_model
      }
      env {
        name  = "ENABLE_GROUNDING"
        value = "true"
      }
      env {
        name  = "LLM_TEMPERATURE"
        value = "0.3"
      }
      env {
        name  = "LLM_MAX_RETRIES"
        value = "3"
      }

      # ── Secrets from Secret Manager ────────────────────────────────────────
      dynamic "env" {
        for_each = local.secret_env_vars
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.app_secrets[env.value].secret_id
              version = "latest"
            }
          }
        }
      }

      # Startup probe: allow up to 2 minutes for the app to start
      startup_probe {
        http_get {
          path = "/_stcore/health"
          port = 8501
        }
        initial_delay_seconds = 10
        period_seconds        = 10
        failure_threshold     = 12
        timeout_seconds       = 5
      }

      # Liveness probe: restart if the app becomes unresponsive
      liveness_probe {
        http_get {
          path = "/_stcore/health"
          port = 8501
        }
        period_seconds    = 30
        failure_threshold = 3
        timeout_seconds   = 5
      }
    }

    # Give the app enough time to finish generating a presentation
    timeout = "600s"
  }

  depends_on = [
    google_project_service.apis,
    google_artifact_registry_repository.docker_repo,
    google_secret_manager_secret_version.app_secret_values,
  ]

  lifecycle {
    # Don't override the image set by GitHub Actions on each deploy
    ignore_changes = [template[0].containers[0].image]
  }
}

# ─── Allow unauthenticated public access ─────────────────────────────────────

resource "google_cloud_run_v2_service_iam_member" "public_access" {
  project  = google_cloud_run_v2_service.ppt_builder.project
  location = google_cloud_run_v2_service.ppt_builder.location
  name     = google_cloud_run_v2_service.ppt_builder.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
