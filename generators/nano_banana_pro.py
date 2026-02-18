"""
generators/nano_banana_pro.py — Visual generation & refinement via Gemini image API.
Uses the google-genai SDK's generate_content() with image modality.
Supports:
  1. Text-to-image: Generate infographics from text prompts
  2. Image-to-image: Refine existing slide renders with AI polish
Falls back gracefully when generation fails or is unavailable.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Optional
from utils.gcp_storage import get_storage_manager

from google import genai
from google.genai import types
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

if TYPE_CHECKING:
    from generators.themes import PresentationTheme

from config import Settings, get_settings
from engine.pipeline_logger import PipelineLogger


class NanoBananaProIntegration:
    """Generates and refines slide visuals via Gemini Image API.

    Uses the same gemini_api_key as the text LLM — no separate key needed.
    Falls back gracefully when generation fails or is unavailable.
    """

    GEMINI_IMAGE_MODEL = "gemini-3-pro-image-preview"

    def __init__(
        self,
        api_key: Optional[str] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._log = PipelineLogger("NanoBananaPro")
        self._settings = settings or get_settings()
        self._api_key = api_key or self._settings.gemini_api_key
        self._available = self._api_key is not None and self._api_key.strip() != ""

        if self._available:
            self._client = genai.Client(api_key=self._api_key)
            self._log.info("Imagen integration enabled (using Gemini API key)")
        else:
            self._client = None
            self._log.info("Imagen not configured — infographic generation disabled")

    @property
    def is_available(self) -> bool:
        return self._available

    # ── Low-level API calls ──────────────────────────────────

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=2, min=2, max=15),
        reraise=True,
    )
    def _call_gemini_image(self, prompt: str) -> Optional[bytes]:
        """Call the Gemini image generation API (text-to-image) with retry."""
        response = self._client.models.generate_content(
            model=self.GEMINI_IMAGE_MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data.mime_type.startswith(
                "image/"
            ):
                return part.inline_data.data
        return None

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=2, min=2, max=15),
        reraise=True,
    )
    def _call_gemini_image_refine(
        self, image_bytes: bytes, prompt: str
    ) -> Optional[bytes]:
        """Call the Gemini image API with an input image (image-to-image refinement)."""
        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        response = self._client.models.generate_content(
            model=self.GEMINI_IMAGE_MODEL,
            contents=[image_part, prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data.mime_type.startswith(
                "image/"
            ):
                return part.inline_data.data
        return None

    # ── Text-to-image generation ─────────────────────────────

    def generate_visual(
        self,
        prompt: str,
        width: int = 1920,
        height: int = 1080,
        placement: str = "full-slide",
        theme: Optional["PresentationTheme"] = None,
    ) -> Optional[io.BytesIO]:
        """Generate an infographic image from a text prompt.

        Args:
            prompt: Detailed visual generation prompt.
            width: Target width in pixels.
            height: Target height in pixels.
            placement: One of 'full-slide', 'right-column', 'bottom-section'.

        Returns:
            BytesIO PNG image buffer if successful, None otherwise.
        """
        if not self._available:
            self._log.debug("Imagen unavailable, skipping visual generation")
            return None

        dimension_map = {
            "full-slide": "16:9 widescreen landscape",
            "right-column": "3:4 portrait",
            "bottom-section": "16:9 widescreen landscape",
        }
        dimension_hint = dimension_map.get(placement, "16:9 widescreen landscape")

        theme_hint = ""
        if theme:
            theme_hint = (
                f"COLOR THEME: Use primary color {theme.primary_hex}, "
                f"accent color {theme.accent_hex}, "
                f"background color {theme.bg_white_hex}, "
                f"text color {theme.text_dark_hex}. "
                f"Apply these exact colors throughout the design. "
            )

        if placement == "full-slide":
            enhanced_prompt = (
                f"{prompt}\n\n"
                f"{theme_hint}"
                f"Output format: {dimension_hint}, high-resolution, presentation-ready."
            )
        else:
            enhanced_prompt = (
                f"Professional financial infographic for a presentation slide. "
                f"Clean, modern flat design. Eye-catching visual layout with icons, "
                f"color blocks, geometric shapes, and clear visual hierarchy. "
                f"Whitespace-rich, high contrast, suitable for projection. "
                f"{theme_hint}"
                f"{prompt}"
                f" Create in {dimension_hint} format."
            )

        self._log.action(
            "Generate Infographic",
            f"format={dimension_hint}, placement={placement}",
        )

        try:
            image_bytes = self._call_gemini_image(enhanced_prompt)
            if image_bytes is None:
                self._log.warning("Gemini image generation returned no image part")
                return None
            buf = io.BytesIO(image_bytes)
            buf.seek(0)
            self._log.info(f"Infographic generated: {len(image_bytes) / 1024:.1f} KB")

            # Upload to GCS if configured (fire and forget basically, just store it)
            try:
                storage = get_storage_manager()
                if storage.enabled:
                    # We need a fresh copy of bytes or just use image_bytes
                    filename = storage.generate_unique_filename("images/infographics", ".png")
                    storage.upload_file(image_bytes, filename, content_type="image/png")
            except Exception as e:
                self._log.warning(f"Failed to upload infographic to GCS: {e}")

            return buf
        except Exception as e:
            self._log.warning(f"Gemini image generation failed: {e}")
            return None

    # ── Image-to-image refinement ────────────────────────────

    def refine_slide(
        self,
        slide_image: bytes,
        refinement_prompt: str,
    ) -> Optional[io.BytesIO]:
        """Refine a rendered slide image via Gemini image-to-image.

        Takes an existing slide render (PNG) and a refinement prompt,
        and returns a visually polished version.

        Args:
            slide_image: PNG bytes of the rendered slide.
            refinement_prompt: Instructions for refinement (theme, style).

        Returns:
            BytesIO PNG image buffer if successful, None otherwise.
        """
        if not self._available:
            self._log.debug("Imagen unavailable, skipping slide refinement")
            return None

        self._log.action("Refine Slide", f"input={len(slide_image) / 1024:.0f} KB")

        try:
            refined_bytes = self._call_gemini_image_refine(
                slide_image, refinement_prompt
            )
            if refined_bytes is None:
                self._log.warning("Gemini refinement returned no image part")
                return None
            buf = io.BytesIO(refined_bytes)
            buf.seek(0)
            self._log.info(f"Slide refined: {len(refined_bytes) / 1024:.1f} KB")

            # Upload to GCS if configured
            try:
                storage = get_storage_manager()
                if storage.enabled:
                    filename = storage.generate_unique_filename("images/refined_slides", ".png")
                    storage.upload_file(refined_bytes, filename, content_type="image/png")
            except Exception as e:
                self._log.warning(f"Failed to upload refined slide to GCS: {e}")

            return buf
        except Exception as e:
            self._log.warning(f"Gemini slide refinement failed: {e}")
            return None
