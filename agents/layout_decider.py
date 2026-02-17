"""
agents/layout_decider.py — Visual type confirmation/override logic.
Ensures each slide has the optimal layout and visual type based on content.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from config import Settings, get_settings
from engine.llm_provider import LLMProvider
from engine.pipeline_logger import PipelineLogger
from models import SlidePlan
from prompts.content_prompts import LAYOUT_DECISION_PROMPT


class LayoutDecision(BaseModel):
    recommended_layout: str
    recommended_visual: str
    reason: str
    changed: bool


class LayoutDecider:
    """Confirms or overrides the planned visual type for each slide."""

    def __init__(
        self,
        llm: Optional[LLMProvider] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._llm = llm or LLMProvider(self._settings)
        self._log = PipelineLogger("LayoutDecider")

    def decide(
        self,
        slide: SlidePlan,
        content_summary: str = "",
        available_data: str = "",
    ) -> SlidePlan:
        """Evaluate and potentially override the slide's layout/visual type.

        Skips LLM call entirely for:
        - user_locked slides (user explicitly set the visual type)
        - title / closing / exec_summary slides (fixed structure)
        - text_heavy_infographic slides (must stay as infographic)

        Args:
            slide: The current SlidePlan.
            content_summary: Summary of the slide's generated content.
            available_data: Description of available data for this slide.

        Returns:
            Updated SlidePlan with confirmed or overridden layout/visual.
        """
        self._log.action("Layout Decision", f"slide={slide.id}: {slide.title}")

        # Skip override for user-locked slides
        if getattr(slide, "user_locked", False):
            self._log.info(
                f"Slide {slide.id}: SKIPPED — user locked "
                f"({slide.layout_type}/{slide.visual_type})"
            )
            return slide

        # Skip override for special layout types
        if slide.layout_type in ("title", "closing", "exec_summary"):
            self._log.info(
                f"Slide {slide.id}: SKIPPED — {slide.layout_type} is a fixed layout"
            )
            return slide

        # Skip override for text_heavy_infographic
        if slide.visual_type == "text_heavy_infographic":
            self._log.info(
                f"Slide {slide.id}: SKIPPED — text_heavy_infographic must not be overridden"
            )
            return slide

        prompt = LAYOUT_DECISION_PROMPT.format(
            slide_title=slide.title,
            planned_layout=slide.layout_type,
            planned_visual=slide.visual_type,
            content_summary=content_summary or "; ".join(slide.content_bullets),
            available_data=available_data or slide.data_source_query,
        )

        try:
            decision = self._llm.generate_structured(
                prompt=prompt,
                response_model=LayoutDecision,
            )

            if decision.changed:
                self._log.decision(
                    f"Layout override for slide {slide.id}: "
                    f"{slide.layout_type}/{slide.visual_type} → "
                    f"{decision.recommended_layout}/{decision.recommended_visual}",
                    reason=decision.reason,
                )
                slide.layout_type = decision.recommended_layout
                slide.visual_type = decision.recommended_visual
            else:
                self._log.info(f"Layout confirmed for slide {slide.id}")
        except Exception as e:
            self._log.warning(f"Layout decision failed for slide {slide.id}: {e}")

        return slide
