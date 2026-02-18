# ─── Outputs ─────────────────────────────────────────────────────────────────
# Copy these values into your GitHub repository secrets after terraform apply.

output "cloud_run_url" {
  description = "Public URL of the deployed PPT Builder app"
  value       = google_cloud_run_v2_service.ppt_builder.uri
}

output "gcs_bucket_name" {
  description = "GCS bucket name for generated artifacts"
  value       = google_storage_bucket.artifacts.name
}

output "artifact_registry_url" {
  description = "Docker registry URL (use in GitHub Actions)"
  value       = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/ppt-builder/app"
}

output "github_secret_workload_identity_provider" {
  description = "→ Add as GitHub Secret: GCP_WORKLOAD_IDENTITY_PROVIDER"
  value       = google_iam_workload_identity_pool_provider.github_actions.name
}

output "github_secret_service_account" {
  description = "→ Add as GitHub Secret: GCP_SERVICE_ACCOUNT"
  value       = google_service_account.github_actions_sa.email
}

output "github_secret_gcp_project_id" {
  description = "→ Add as GitHub Secret: GCP_PROJECT_ID"
  value       = var.gcp_project_id
}

output "github_secret_gcp_region" {
  description = "→ Add as GitHub Secret: GCP_REGION"
  value       = var.gcp_region
}
