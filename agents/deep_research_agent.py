"""
agents/deep_research_agent.py — Targeted slide-specific research using grounded search.
Retrieves specific data points, statistics, and chart-ready data for individual slides.
"""

from __future__ import annotations

from typing import List, Optional

from config import Settings, get_settings
from engine.llm_provider import LLMProvider
from engine.pipeline_logger import PipelineLogger
from engine.research_engine import GroundedResearchEngine
from models import ResearchFinding, SlidePlan
from prompts.research_prompts import DEEP_RESEARCH_PROMPT


class DeepResearchAgent:
    """Performs focused, slide-specific research to fill data gaps."""

    def __init__(
        self,
        llm: Optional[LLMProvider] = None,
        research_engine: Optional[GroundedResearchEngine] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._llm = llm or LLMProvider(self._settings)
        self._engine = research_engine or GroundedResearchEngine(
            llm=self._llm, settings=self._settings
        )
        self._log = PipelineLogger("DeepResearchAgent")

    def research_slide(
        self,
        slide: SlidePlan,
        existing_context: str = "",
    ) -> ResearchFinding:
        """Perform deep research for a specific slide's data needs.

        Args:
            slide: The SlidePlan that needs specific data.
            existing_context: Already-known context to avoid redundant searching.

        Returns:
            A ResearchFinding with targeted data for the slide.
        """
        self._log.action("Deep Research", f"slide={slide.id}: {slide.title}")

        # Determine the data type from visual requirements
        data_type = self._infer_data_type(slide)

        prompt = DEEP_RESEARCH_PROMPT.format(
            slide_title=slide.title,
            data_type=data_type,
            key_insight=slide.key_insight,
            existing_context=existing_context[:2000] if existing_context else "None",
        )

        # Use grounded search for factual data
        result = self._llm.generate_with_search(
            query=prompt,
            model=self._settings.gemini_pro_model,  # Use pro model for deep research
            system_instruction=(
                "You are a specialist financial data researcher. "
                "Provide exact numbers, dates, percentages, and source citations. "
                "Format data points clearly for chart/table extraction."
            ),
        )

        finding = ResearchFinding(
            topic=slide.title,
            content=result["text"],
            sources=result["grounding_sources"],
            confidence=self._engine._estimate_confidence(
                result["text"], result["grounding_sources"]
            ),
        )

        self._log.info(
            f"Deep research for slide {slide.id}: "
            f"{len(finding.sources)} sources, confidence={finding.confidence:.2f}"
        )
        return finding

    def research_slides_batch(
        self,
        slides: List[SlidePlan],
        shared_context: str = "",
        max_workers: int = 3,
    ) -> List[ResearchFinding]:
        """Research multiple slides that need data (filters to slides with data_source_query).

        Args:
            slides: List of SlidePlan objects.
            shared_context: Context shared across all slide research.
            max_workers: Max concurrent research threads.

        Returns:
            List of ResearchFinding objects, one per researched slide.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Only research slides that actually need data
        data_slides = [s for s in slides if s.data_source_query.strip()]
        self._log.action(
            "Batch Deep Research",
            f"{len(data_slides)}/{len(slides)} slides need data",
        )

        if not data_slides:
            return []

        findings: List[Optional[ResearchFinding]] = [None] * len(data_slides)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(self.research_slide, slide, shared_context): i
                for i, slide in enumerate(data_slides)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    findings[idx] = future.result()
                except Exception as e:
                    self._log.error(f"Deep research failed for slide: {e}")
                    findings[idx] = ResearchFinding(
                        topic=data_slides[idx].title,
                        content=f"Deep research failed: {e}",
                        sources=[],
                        confidence=0.0,
                    )

        return [f for f in findings if f is not None]

    @staticmethod
    def _infer_data_type(slide: SlidePlan) -> str:
        """Infer the type of data needed based on slide configuration."""
        visual = slide.visual_type.lower()
        if "chart" in visual:
            return "quantitative data suitable for charting (exact numbers, time series, or category comparisons)"
        if visual == "table":
            return "structured comparison data suitable for a table format"
        if slide.layout_type == "exec_summary":
            return "key metrics and KPI values for an executive summary"
        return "qualitative insights with supporting statistics"
