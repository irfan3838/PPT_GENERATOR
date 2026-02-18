"""
agents/slide_render_decider.py — Deciding agent for slide render strategy.
Analyzes each slide's content and decides: image_generation (text-heavy) vs standard (data-heavy).

Decision logic (deterministic, no LLM call):
  - title / exec_summary / closing → ALWAYS standard (themed gradient rendering)
  - visual_type == "text_heavy_infographic" → ALWAYS image_generation (nano banana pro)
  - slides with chart_data or table_data → ALWAYS standard (matplotlib/pptx)
  - bullet slides without charts/tables → image_generation (eye-catching infographic)
  - all other slides → standard
"""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import Settings, get_settings
from engine.pipeline_logger import PipelineLogger
from models import RenderDecision, SlidePlan
from prompts.render_decision_prompts import IMAGE_SLIDE_PROMPT_TEMPLATE

if TYPE_CHECKING:
    from agents.slide_content_agent import SlideContent
    from generators.themes import PresentationTheme

# Layout types that ALWAYS use standard themed rendering (never image generation)
STANDARD_LAYOUT_TYPES = {"title", "closing", "exec_summary"}


class SlideRenderDecider:
    """Decides per-slide whether to generate a full-slide image or use standard rendering."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        **kwargs,
    ) -> None:
        self._settings = settings or get_settings()
        self._log = PipelineLogger("SlideRenderDecider")

    def _build_image_prompt(
        self,
        content: "SlideContent",
        theme: "PresentationTheme",
        slide_num: int,
        total_slides: int,
    ) -> str:
        """Build a detailed image generation prompt for nano banana pro."""
        max_bullets = 5
        bullets_to_show = content.content_bullets[:max_bullets]
        bullets_text = "\n".join(f"- {b}" for b in bullets_to_show)
        return IMAGE_SLIDE_PROMPT_TEMPLATE.format(
            slide_title=content.title,
            content_bullets=bullets_text,
            key_insight=content.key_insight or "N/A",
            speaker_notes=content.speaker_notes[:500]
            if content.speaker_notes
            else "N/A",
            primary_color=theme.primary_hex,
            accent_color=theme.accent_hex,
            bg_color=theme.bg_white_hex,
            text_color=theme.text_dark_hex,
            slide_num=slide_num,
            total_slides=total_slides,
        )

    def decide_single(
        self,
        slide: SlidePlan,
        content: "SlideContent",
        theme: "PresentationTheme",
        slide_num: int,
        total_slides: int,
    ) -> RenderDecision:
        """Decide render strategy for a single slide."""
        self._log.action("Render Decision", f"slide={slide.id}: {slide.title}")

        # ── Rule 1: Title, Exec Summary, Closing → ALWAYS standard ──
        if slide.layout_type in STANDARD_LAYOUT_TYPES:
            self._log.info(
                f"Slide {slide.id}: render_mode=standard "
                f"({slide.layout_type} uses themed rendering)"
            )
            return RenderDecision(
                slide_id=slide.id,
                render_mode="standard",
                reason=f"{slide.layout_type} slides use themed gradient rendering",
                confidence=1.0,
            )

        # ── Rule 2: text_heavy_infographic → ALWAYS image_generation ──
        # This is the explicit user signal: "I want this slide as a nano banana infographic"
        if slide.visual_type == "text_heavy_infographic":
            image_prompt = self._build_image_prompt(
                content, theme, slide_num, total_slides
            )
            self._log.info(
                f"Slide {slide.id}: render_mode=image_generation "
                f"(text_heavy_infographic → nano banana pro)"
            )
            return RenderDecision(
                slide_id=slide.id,
                render_mode="image_generation",
                reason="User selected text_heavy_infographic — full-slide AI image via nano banana pro",
                image_prompt=image_prompt,
                confidence=1.0,
            )

        # ── Rule 3: Slides with chart/table data → standard ──
        if content.chart_data or content.table_data:
            self._log.info(
                f"Slide {slide.id}: render_mode=standard (has chart/table data)"
            )
            return RenderDecision(
                slide_id=slide.id,
                render_mode="standard",
                reason="Slide has structured chart/table data — standard matplotlib/pptx rendering",
                confidence=1.0,
            )

        # ── Rule 4: Bullet/split slides without data → image_generation ──
        # These are text-heavy qualitative slides that benefit from AI-generated visuals
        if slide.layout_type in ("bullet", "split"):
            image_prompt = self._build_image_prompt(
                content, theme, slide_num, total_slides
            )
            self._log.info(
                f"Slide {slide.id}: render_mode=image_generation "
                f"(text-heavy {slide.layout_type} → AI infographic)"
            )
            return RenderDecision(
                slide_id=slide.id,
                render_mode="image_generation",
                reason=f"Text-heavy {slide.layout_type} slide — AI-generated infographic for eye-catching design",
                image_prompt=image_prompt,
                confidence=1.0,
            )

        # ── Default: standard rendering ──
        self._log.info(
            f"Slide {slide.id}: render_mode=standard (default for {slide.layout_type})"
        )
        return RenderDecision(
            slide_id=slide.id,
            render_mode="standard",
            reason=f"Default standard rendering for {slide.layout_type}",
            confidence=0.9,
        )

    def decide_all(
        self,
        slides: List[SlidePlan],
        contents: List["SlideContent"],
        theme: "PresentationTheme",
        max_workers: int = 5,
    ) -> List[RenderDecision]:
        """Decide render strategy for all slides in parallel."""
        self._log.action("Render Decisions", f"{len(slides)} slides")
        total = len(slides)
        decisions: List[Optional[RenderDecision]] = [None] * total

        def _decide_one(idx: int) -> tuple:
            slide = slides[idx]
            content = contents[idx]
            decision = self.decide_single(slide, content, theme, idx + 1, total)
            return idx, decision

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_decide_one, i): i for i in range(total)}
            for future in as_completed(futures):
                try:
                    idx, decision = future.result()
                    decisions[idx] = decision
                except Exception as e:
                    idx = futures[future]
                    self._log.error(f"Decision failed for slide idx {idx}: {e}")
                    decisions[idx] = RenderDecision(
                        slide_id=slides[idx].id,
                        render_mode="standard",
                        reason=f"Error fallback: {e}",
                        confidence=0.5,
                    )

        final = [d for d in decisions if d is not None]
        image_count = sum(1 for d in final if d.render_mode == "image_generation")
        self._log.info(
            f"Decisions: {image_count} image_generation, {len(final) - image_count} standard"
        )
        return final
