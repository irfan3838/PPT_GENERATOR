# ─── GCS Bucket: Generated artifacts (PPTX, images) ─────────────────────────

resource "google_storage_bucket" "artifacts" {
  name          = "${var.gcp_project_id}-ppt-builder-artifacts"
  location      = var.gcp_region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  # Auto-delete old non-current versions after 30 days
  lifecycle_rule {
    condition {
      num_newer_versions = 3
    }
    action {
      type = "Delete"
    }
  }

  # Auto-delete generated files older than 90 days
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD"]
    response_header = ["Content-Type"]
    max_age_seconds = 3600
  }

  depends_on = [google_project_service.apis]
}

# ─── GCS Bucket: Terraform state (create manually before first apply) ─────────
# This bucket is managed separately. Create it via gcloud before running terraform:
#   gcloud storage buckets create gs://YOUR_STATE_BUCKET --project=YOUR_PROJECT
