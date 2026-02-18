# ─── Secret Manager: Application secrets ─────────────────────────────────────
# Secret resources are created by Terraform; values are stored in Secret Manager.
# Terraform receives sensitive values via variables (tfvars or env vars).

locals {
  secrets = {
    "ppt-builder-gemini-api-key"      = var.gemini_api_key
    "ppt-builder-nano-banana-api-key" = var.nano_banana_api_key
    "ppt-builder-gmail-email"         = var.gmail_sender_email
    "ppt-builder-gmail-password"      = var.gmail_sender_password
  }
}

resource "google_secret_manager_secret" "app_secrets" {
  for_each  = local.secrets
  secret_id = each.key

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "app_secret_values" {
  for_each    = local.secrets
  secret      = google_secret_manager_secret.app_secrets[each.key].id
  secret_data = each.value

  # Prevent Terraform from showing diffs when secret value changes externally
  lifecycle {
    ignore_changes = [secret_data]
  }
}
