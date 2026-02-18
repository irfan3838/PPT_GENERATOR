# Deployment Guide — PPT Builder

## Prerequisites

Install these tools before starting:

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- A GCP project with billing enabled
- A GitHub repository with this code

---

## Step 1 — Authenticate gcloud locally

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

---

## Step 2 — Enable APIs (one-time, done by Terraform — but run this first)

```bash
gcloud services enable cloudresourcemanager.googleapis.com
```

> Terraform enables all other required APIs automatically.

---

## Step 3 — Create a Terraform state bucket (one-time)

Terraform needs a GCS bucket to store its state file. Create it manually before the first `terraform apply`:

```bash
gcloud storage buckets create gs://YOUR_PROJECT_ID-tf-state \
  --project=YOUR_PROJECT_ID \
  --location=us-central1 \
  --uniform-bucket-level-access
```

Then uncomment the `backend "gcs"` block in `terraform/main.tf` and set the bucket name:

```hcl
backend "gcs" {
  bucket = "YOUR_PROJECT_ID-tf-state"
  prefix = "ppt-builder/state"
}
```

---

## Step 4 — Configure Terraform variables

```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
```

Edit `terraform/terraform.tfvars` with your real values:

```hcl
gcp_project_id = "your-gcp-project-id"
gcp_region     = "us-central1"
environment    = "prod"

github_owner = "your-github-username"
github_repo  = "your-repo-name"

gemini_api_key        = "AIza..."
nano_banana_api_key   = "AIza..."        # leave "" if unused
gmail_sender_email    = "you@gmail.com"  # leave "" if unused
gmail_sender_password = "xxxx xxxx xxxx xxxx"
```

> **Never commit `terraform.tfvars`** — it is already in `.gitignore`.

---

## Step 5 — Run Terraform

```bash
cd terraform

terraform init
terraform plan    # review what will be created
terraform apply   # type "yes" to confirm
```

### What Terraform creates

| Resource | Name |
|---|---|
| GCS Bucket | `YOUR_PROJECT_ID-ppt-builder-artifacts` |
| Secret Manager | `ppt-builder-gemini-api-key`, `ppt-builder-nano-banana-api-key`, `ppt-builder-gmail-email`, `ppt-builder-gmail-password` |
| Artifact Registry | `ppt-builder` (Docker) |
| Cloud Run Service | `ppt-builder` |
| Service Accounts | `ppt-builder-runtime`, `ppt-builder-github-actions` |
| Workload Identity | `ppt-builder-github-pool` |

---

## Step 6 — Copy Terraform outputs to GitHub Secrets

After `terraform apply` completes, it prints four values. Add them as secrets in your GitHub repository:

**GitHub → Settings → Secrets and variables → Actions → New repository secret**

| GitHub Secret Name | Value (from Terraform output) |
|---|---|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `github_secret_workload_identity_provider` |
| `GCP_SERVICE_ACCOUNT` | `github_secret_service_account` |
| `GCP_PROJECT_ID` | `github_secret_gcp_project_id` |
| `GCP_REGION` | `github_secret_gcp_region` |

To print outputs again at any time:

```bash
cd terraform && terraform output
```

---

## Step 7 — First deployment

Push to `main` to trigger the deployment pipeline:

```bash
git checkout main
git push origin main
```

GitHub Actions will:
1. Authenticate to GCP via Workload Identity (no stored keys)
2. Build the Docker image
3. Push it to Artifact Registry
4. Deploy to Cloud Run

Monitor progress at: `https://github.com/YOUR_ORG/YOUR_REPO/actions`

---

## CI/CD Workflows

### `ci.yml` — runs on every PR and push to `main`

- Ruff linting
- All module import validation

### `deploy.yml` — runs on push to `main` only

- GCP auth via OIDC Workload Identity
- Docker build + push to Artifact Registry
- `gcloud run deploy` with the new image SHA

---

## Accessing the app

After deployment, get the URL:

```bash
gcloud run services describe ppt-builder \
  --region=YOUR_REGION \
  --project=YOUR_PROJECT_ID \
  --format="value(status.url)"
```

Or check the GitHub Actions run summary — the URL is printed there after each deploy.

---

## Local development

```bash
# Clone and set up
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy and fill in env vars
cp terraform/terraform.tfvars.example .env.local
# Set GEMINI_API_KEY and other vars in .env

# Run the app
streamlit run app.py
```

---

## Updating secrets

To rotate an API key, update it in Secret Manager directly — no Terraform needed:

```bash
echo -n "NEW_API_KEY_VALUE" | \
  gcloud secrets versions add ppt-builder-gemini-api-key --data-file=-
```

Cloud Run picks up `latest` version automatically on the next request.

---

## Tearing down

```bash
cd terraform
terraform destroy   # deletes all resources except the state bucket
```

To also delete the state bucket:

```bash
gcloud storage rm -r gs://YOUR_PROJECT_ID-tf-state
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `terraform apply` fails on API enablement | Wait 60s and retry — GCP API activation can be slow |
| Docker push fails in GitHub Actions | Confirm `GCP_WORKLOAD_IDENTITY_PROVIDER` and `GCP_SERVICE_ACCOUNT` secrets are set correctly |
| Cloud Run returns 503 on startup | Check logs: `gcloud run services logs read ppt-builder --region=YOUR_REGION` |
| Streamlit not loading | Ensure port 8501 is exposed and `--server.address=0.0.0.0` is set in Dockerfile CMD |
| Secret not found at runtime | Verify the Cloud Run SA has `roles/secretmanager.secretAccessor` and the secret version is `enabled` |
