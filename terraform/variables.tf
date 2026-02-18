# ─── Project ─────────────────────────────────────────────────────────────────

variable "gcp_project_id" {
  description = "Your GCP project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP region for all resources (e.g. us-central1, asia-south1)"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Deployment environment (prod, staging)"
  type        = string
  default     = "prod"
}

# ─── GitHub (for Workload Identity) ──────────────────────────────────────────

variable "github_owner" {
  description = "GitHub username or org that owns the repository (e.g. myorg)"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name without owner (e.g. ppt-builder)"
  type        = string
}

# ─── App secrets ─────────────────────────────────────────────────────────────

variable "gemini_api_key" {
  description = "Google Gemini API key"
  type        = string
  sensitive   = true
}

variable "nano_banana_api_key" {
  description = "Nano Banana Pro API key (optional image generation service)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "gmail_sender_email" {
  description = "Gmail address used to send presentations via email"
  type        = string
  sensitive   = true
  default     = ""
}

variable "gmail_sender_password" {
  description = "Gmail app password for SMTP (not your regular Gmail password)"
  type        = string
  sensitive   = true
  default     = ""
}

# ─── App config ──────────────────────────────────────────────────────────────

variable "gemini_flash_model" {
  description = "Gemini Flash model identifier"
  type        = string
  default     = "gemini-2.0-flash"
}

variable "gemini_pro_model" {
  description = "Gemini Pro model identifier"
  type        = string
  default     = "gemini-2.0-pro-exp"
}

variable "cloud_run_min_instances" {
  description = "Minimum Cloud Run instances (0 = scale to zero when idle)"
  type        = number
  default     = 0
}

variable "cloud_run_max_instances" {
  description = "Maximum Cloud Run instances"
  type        = number
  default     = 3
}
