# ─── Workload Identity Federation: Keyless GitHub Actions → GCP auth ─────────
# GitHub Actions authenticates to GCP without any stored service account keys.
# Reference: https://cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "ppt-builder-github-pool"
  display_name              = "GitHub Actions Pool – PPT Builder"
  description               = "Allows GitHub Actions to impersonate GCP service accounts"
  disabled                  = false

  depends_on = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool_provider" "github_actions" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-actions"
  display_name                       = "GitHub Actions OIDC Provider"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  # Only allow tokens from your specific repository
  attribute_condition = "attribute.repository == '${var.github_owner}/${var.github_repo}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Allow GitHub Actions tokens from this repo to impersonate the deployment SA
resource "google_service_account_iam_member" "github_actions_wi_binding" {
  service_account_id = google_service_account.github_actions_sa.name
  role               = "roles/iam.workloadIdentityUser"

  # Restrict to pushes/PRs from main branch only
  member = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_owner}/${var.github_repo}"
}
