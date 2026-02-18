"""
config.py — Central configuration for PPT Builder v1.
Loads settings from environment variables / .env file.
"""

from datetime import date
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field

# ── Date Awareness ────────────────────────────────────────────
# Computed once at import time so all agents share the same date context.
CURRENT_DATE_STR = date.today().strftime("%B %d, %Y")   # e.g. "February 17, 2026"
CURRENT_YEAR = date.today().year


# ── Project Paths ──────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = DATA_DIR / "output"
LOG_DIR = DATA_DIR / "logs"
CACHE_DIR = DATA_DIR / "cache"

# Ensure data subdirectories exist at import time
for _dir in (OUTPUT_DIR, LOG_DIR, CACHE_DIR):
    _dir.mkdir(parents=True, exist_ok=True)


# ── Application Settings ──────────────────────────────────────
class Settings(BaseSettings):
    """Typed application settings — loaded from env vars / .env file."""

    # --- Gemini API ---
    gemini_api_key: str = Field(
        ..., description="Google Gemini API key"
    )
    gemini_flash_model: str = Field(
        default="gemini-3-flash-preview",
        description="Fast model for routine tasks",
    )
    gemini_pro_model: str = Field(
        default="gemini-3-pro-preview",
        description="Reasoning model for complex analysis",
    )

    # --- LLM Behaviour ---
    llm_temperature: float = Field(
        default=0.3, ge=0.0, le=2.0,
        description="Default sampling temperature",
    )
    llm_max_retries: int = Field(
        default=3, ge=1,
        description="Max retries on transient API failures",
    )
    llm_retry_wait_seconds: int = Field(
        default=2, ge=1,
        description="Base wait between retries (exponential backoff)",
    )
    llm_max_output_tokens: int = Field(
        default=8192, ge=256,
        description="Default max output tokens per LLM call",
    )

    # --- Grounded Search ---
    enable_grounding: bool = Field(
        default=True,
        description="Enable Gemini grounded search for research agents",
    )

    # --- Presentation Defaults ---
    default_slide_width_inches: float = Field(default=13.333)
    default_slide_height_inches: float = Field(default=7.5)
    chart_dpi: int = Field(default=200, description="Matplotlib chart DPI")

    # --- Optional: Nano Banana Pro ---
    nano_banana_api_key: Optional[str] = Field(
        default=None,
        description="API key for Nano Banana Pro (optional enhanced visuals)",
    )

    # --- Google Cloud Storage ---
    gcp_project_id: Optional[str] = Field(
        default=None,
        description="GCP Project ID for storage bucket",
    )
    gcp_bucket_name: Optional[str] = Field(
        default=None,
        description="GCP Storage Bucket Name to save artifacts",
    )
    gcp_credentials_json: Optional[str] = Field(
        default=None,
        description="Path to GCP Service Account JSON key (optional)",
    )

    model_config = {
        "env_file": str(ROOT_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


def get_settings() -> Settings:
    """Factory that loads and returns validated settings."""
    return Settings()  # type: ignore[call-arg]
