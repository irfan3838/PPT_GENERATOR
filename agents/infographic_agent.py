"""
agents/infographic_agent.py — Infographic decision-making and prompt generation.
Analyzes slide content to recommend and generate infographic prompts.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from config import Settings, get_settings
from engine.llm_provider import LLMProvider
from engine.pipeline_logger import PipelineLogger
from models import InfographicProposal
from prompts.infographic_prompts import INFOGRAPHIC_DECISION_PROMPT


class InfographicAgent:
    """Decides whether slides benefit from infographics and generates prompts."""

    def __init__(
        self,
        llm: Optional[LLMProvider] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._llm = llm or LLMProvider(self._settings)
        self._log = PipelineLogger("InfographicAgent")

    def evaluate_slide(
        self,
        slide_number: int,
        slide_title: str,
        layout_type: str,
        content_summary: str,
        data_summary: str,
    ) -> InfographicProposal:
        """Evaluate a single slide for infographic potential.

        Args:
            slide_number: Slide index.
            slide_title: The slide title.
            layout_type: Current layout type.
            content_summary: Summary of slide content.
            data_summary: Summary of available data.

        Returns:
            InfographicProposal with recommendation and generated prompt.
        """
        self._log.action("Evaluate Infographic", f"slide #{slide_number}")

        prompt = INFOGRAPHIC_DECISION_PROMPT.format(
            slide_number=slide_number,
            slide_title=slide_title,
            layout_type=layout_type,
            content_summary=content_summary[:2000],
            data_summary=data_summary[:2000],
        )

        proposal = self._llm.generate_structured(
            prompt=prompt,
            response_model=InfographicProposal,
            system_instruction=(
                "You are a visual design strategist. "
                "Recommend infographics only when they add clear value. "
                "Generate detailed, actionable prompts for image generation."
            ),
        )

        if proposal.infographic_recommended:
            self._log.decision(
                f"Infographic recommended for slide {slide_number}: "
                f"type={proposal.infographic_type}, "
                f"placement={proposal.placement}",
                reason=proposal.reason,
            )
        else:
            self._log.info(f"No infographic needed for slide {slide_number}")

        return proposal

    def evaluate_all_slides(
        self,
        slides_content: List[Dict[str, Any]],
        max_workers: int = 3,
    ) -> List[InfographicProposal]:
        """Evaluate all slides for infographic enrichment (concurrently).

        Args:
            slides_content: List of slide content dicts.
            max_workers: Max concurrent evaluation threads.

        Returns:
            List of InfographicProposal objects.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        self._log.action("Batch Infographic Evaluation", f"{len(slides_content)} slides")

        # Filter slides eligible for infographics
        eligible = [
            sd for sd in slides_content
            if sd.get("layout_type", "") not in ("title",)
        ]

        if not eligible:
            return []

        proposals: List[Optional[InfographicProposal]] = [None] * len(eligible)

        def _evaluate_one(idx: int, slide_data: Dict[str, Any]):
            return idx, self.evaluate_slide(
                slide_number=slide_data.get("id", 0),
                slide_title=slide_data.get("title", ""),
                layout_type=slide_data.get("layout_type", ""),
                content_summary="; ".join(slide_data.get("content_bullets", [])),
                data_summary=str(slide_data.get("chart_data", slide_data.get("table_data", ""))),
            )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_evaluate_one, i, sd): i
                for i, sd in enumerate(eligible)
            }
            for future in as_completed(futures):
                try:
                    idx, proposal = future.result()
                    proposals[idx] = proposal
                except Exception as e:
                    self._log.error(f"Infographic evaluation failed: {e}")

        final = [p for p in proposals if p is not None]
        recommended_count = sum(1 for p in final if p.infographic_recommended)
        self._log.info(
            f"Infographic evaluation complete: "
            f"{recommended_count}/{len(final)} slides recommended"
        )
        return final
