"""
agents/slide_content_agent.py — Content generation and JSON structuring for individual slides.
Synthesizes research data into final slide content with chart/table data extraction.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from config import Settings, get_settings
from engine.llm_provider import LLMProvider
from engine.pipeline_logger import PipelineLogger
from models import ChartData, SlidePlan, TableData
from prompts.content_prompts import SLIDE_CONTENT_PROMPT, TEXT_HEAVY_INFOGRAPHIC_PROMPT


class _SlideContentLLM(BaseModel):
    """Schema sent to LLM for structured generation (no binary fields)."""
    title: str
    content_bullets: List[str] = Field(default_factory=list)
    key_insight: str = ""
    speaker_notes: str = ""
    chart_data: Optional[ChartData] = None
    table_data: Optional[TableData] = None
    infographic_prompt: str = Field(
        default="",
        description="Image generation prompt for text-heavy infographic slides",
    )


class _InfographicSlideContentLLM(BaseModel):
    """Schema for text-heavy infographic slide content."""
    title: str
    content_bullets: List[str] = Field(default_factory=list)
    key_insight: str = ""
    speaker_notes: str = ""
    infographic_prompt: str = Field(
        default="",
        description="Detailed prompt for generating a beautiful infographic image",
    )


class SlideContent(_SlideContentLLM):
    """Generated content for a single slide (extends LLM schema with runtime fields)."""
    infographic_image: Optional[bytes] = Field(
        default=None,
        exclude=True,
        description="PNG image bytes for infographic, if generated",
    )
    full_slide_image: Optional[bytes] = Field(
        default=None,
        exclude=True,
        description="PNG image bytes for full-slide image generation (entire slide as image)",
    )


class SlideContentAgent:
    """Generates final slide content from research data and slide plans."""

    def __init__(
        self,
        llm: Optional[LLMProvider] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._llm = llm or LLMProvider(self._settings)
        self._log = PipelineLogger("SlideContentAgent")

    def generate_content(
        self,
        slide: SlidePlan,
        research_data: str,
        theme_description: str = "",
    ) -> SlideContent:
        """Generate final content for a single slide.

        Args:
            slide: The SlidePlan blueprint.
            research_data: Research findings relevant to this slide.
            theme_description: Description of the visual theme to guide tone.
        """
        self._log.action("Generate Slide Content", f"slide={slide.id}: {slide.title}")

        is_infographic = slide.visual_type == "text_heavy_infographic"

        if is_infographic:
            prompt = TEXT_HEAVY_INFOGRAPHIC_PROMPT.format(
                slide_title=slide.title,
                key_insight=slide.key_insight,
                content_bullets="; ".join(slide.content_bullets),
                research_data=research_data[:4000],
                theme_description=theme_description,
            )
            # Add instruction to incorporate theme
            system_instruction = (
                "You are a professional presentation content writer specializing in infographics. "
                "Generate content optimized for visual infographic representation. "
                f"The presentation theme is '{theme_description}' — reflect this style in the content tone. "
                "Include a detailed infographic_prompt for image generation. "
                "Respond with valid JSON."
            )
            llm_result = self._llm.generate_structured(
                prompt=prompt,
                response_model=_InfographicSlideContentLLM,
                model=self._settings.gemini_pro_model,
                system_instruction=system_instruction,
            )
        else:
            prompt = SLIDE_CONTENT_PROMPT.format(
                slide_title=slide.title,
                layout_type=slide.layout_type,
                visual_type=slide.visual_type,
                key_insight=slide.key_insight,
                content_bullets="; ".join(slide.content_bullets),
                research_data=research_data[:4000],
                theme_description=theme_description,
            )
            # Add instruction to incorporate theme
            system_instruction = (
                "You are a professional presentation content writer. "
                "Generate precise, data-backed slide content. "
                f"The presentation theme is '{theme_description}' — keep this tone in mind. "
                "If the slide requires a chart or table, provide exact structured data. "
                "Include chart annotations for significant data points when relevant. "
                "Respond with valid JSON."
            )
            llm_result = self._llm.generate_structured(
                prompt=prompt,
                response_model=_SlideContentLLM,
                model=self._settings.gemini_pro_model,
                system_instruction=system_instruction,
            )

        content = SlideContent(**llm_result.model_dump())

        if content.content_bullets:
            content.content_bullets = [
                b for b in content.content_bullets
                if not b.strip().lower().startswith(("[visual]", "[image]", "[chart]"))
            ]

        self._log.info(
            f"Content for slide {slide.id}: "
            f"bullets={len(content.content_bullets)}, "
            f"has_chart={content.chart_data is not None}, "
            f"has_table={content.table_data is not None}"
        )
        return content

    def generate_all(
        self,
        slides: List[SlidePlan],
        research_map: Dict[int, str],
        theme_description: str = "Corporate Blue",
        max_workers: int = 3,
    ) -> List[SlideContent]:
        """Generate content for all slides concurrently.

        Args:
            slides: List of SlidePlan objects.
            research_map: Dict mapping slide.id → research data string.
            theme_description: Description of the visual theme to guide tone.
            max_workers: Max concurrent generation threads.

        Returns:
            List of SlideContent objects matching slide order.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        self._log.action("Generate All Content", f"{len(slides)} slides (Theme: {theme_description})")
        contents: List[Optional[SlideContent]] = [None] * len(slides)

        def _generate_one(idx: int, slide: SlidePlan) -> tuple:
            research_data = research_map.get(slide.id, "")
            content = self.generate_content(slide, research_data, theme_description)
            return idx, content

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_generate_one, i, slide): i
                for i, slide in enumerate(slides)
            }
            for future in as_completed(futures):
                try:
                    idx, content = future.result()
                    contents[idx] = content
                except Exception as e:
                    idx = futures[future]
                    self._log.error(f"Content generation failed for slide {idx}: {e}")
                    contents[idx] = SlideContent(
                        title=slides[idx].title,
                        content_bullets=["Content generation failed"],
                        key_insight="Error during generation",
                    )

        final = [c for c in contents if c is not None]
        self._log.info(f"All {len(final)} slides content generated")
        return final
