# ─── Artifact Registry: Docker image repository ──────────────────────────────

resource "google_artifact_registry_repository" "docker_repo" {
  location      = var.gcp_region
  repository_id = "ppt-builder"
  description   = "Docker images for PPT Builder application"
  format        = "DOCKER"

  cleanup_policies {
    id     = "keep-last-5-tagged"
    action = "KEEP"
    most_recent_versions {
      keep_count = 5
    }
  }

  cleanup_policies {
    id     = "delete-untagged-after-7d"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "604800s" # 7 days
    }
  }

  depends_on = [google_project_service.apis]
}
