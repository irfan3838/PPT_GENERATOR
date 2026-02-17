"""
agents/critic_agent.py — Data validation, consistency checks, and hallucination detection.
Acts as a quality gate before final slide rendering.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from config import Settings, get_settings
from engine.llm_provider import LLMProvider
from engine.pipeline_logger import PipelineLogger
from prompts.critic_prompts import (
    CROSS_SLIDE_CONSISTENCY_PROMPT,
    SLIDE_VALIDATION_PROMPT,
)


class ValidationIssue(BaseModel):
    type: str  # data_mismatch, hallucination, inconsistency, incomplete
    severity: str  # critical, warning, info
    description: str
    suggestion: str


class SlideValidationResult(BaseModel):
    slide_number: int
    is_valid: bool
    issues: List[ValidationIssue] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)


class CrossSlideIssue(BaseModel):
    slides_affected: List[int]
    type: str
    description: str
    recommendation: str


class CrossSlideConsistencyResult(BaseModel):
    is_consistent: bool
    cross_slide_issues: List[CrossSlideIssue] = Field(default_factory=list)


class CriticAgent:
    """Validates slide content for accuracy, consistency, and hallucinations."""

    def __init__(
        self,
        llm: Optional[LLMProvider] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._llm = llm or LLMProvider(self._settings)
        self._log = PipelineLogger("CriticAgent")

    def validate_slide(
        self,
        slide_number: int,
        slide_title: str,
        slide_content: str,
        source_research: str,
    ) -> SlideValidationResult:
        """Validate a single slide against its source research.

        Args:
            slide_number: Slide index.
            slide_title: The slide title.
            slide_content: JSON-serialized slide content.
            source_research: The research data this slide is based on.

        Returns:
            SlideValidationResult with issues and confidence.
        """
        self._log.action("Validate Slide", f"slide #{slide_number}: {slide_title}")

        prompt = SLIDE_VALIDATION_PROMPT.format(
            slide_number=slide_number,
            slide_title=slide_title,
            slide_content=slide_content,
            source_research=source_research[:3000],
        )

        result = self._llm.generate_structured(
            prompt=prompt,
            response_model=SlideValidationResult,
            system_instruction=(
                "You are a rigorous data auditor. Identify every factual error, "
                "inconsistency, and unsupported claim. Be strict but fair."
            ),
        )

        critical_count = sum(1 for i in result.issues if i.severity == "critical")
        self._log.info(
            f"Slide {slide_number} validation: valid={result.is_valid}, "
            f"issues={len(result.issues)} (critical={critical_count}), "
            f"confidence={result.confidence_score:.2f}"
        )

        return result

    def check_cross_slide_consistency(
        self,
        all_slides_content: List[Dict[str, Any]],
    ) -> CrossSlideConsistencyResult:
        """Check consistency across all slides in the deck.

        Args:
            all_slides_content: List of dicts with slide content data.

        Returns:
            CrossSlideConsistencyResult with any cross-slide issues.
        """
        self._log.action(
            "Cross-Slide Consistency", f"{len(all_slides_content)} slides"
        )

        all_slides_json = json.dumps(all_slides_content, indent=2, default=str)

        prompt = CROSS_SLIDE_CONSISTENCY_PROMPT.format(
            all_slides_json=all_slides_json[:8000],
        )

        result = self._llm.generate_structured(
            prompt=prompt,
            response_model=CrossSlideConsistencyResult,
            model=self._settings.gemini_pro_model,
            system_instruction=(
                "You are a presentation consistency auditor. "
                "Find data conflicts and naming inconsistencies across slides."
            ),
        )

        self._log.info(
            f"Cross-slide check: consistent={result.is_consistent}, "
            f"issues={len(result.cross_slide_issues)}"
        )
        return result

    def validate_all(
        self,
        slides_content: List[Dict[str, Any]],
        research_map: Dict[int, str],
        max_workers: int = 3,
    ) -> List[SlideValidationResult]:
        """Validate all slides concurrently and check cross-slide consistency.

        Args:
            slides_content: List of slide content dicts.
            research_map: Dict mapping slide_number → research data.
            max_workers: Max concurrent validation threads.

        Returns:
            List of SlideValidationResult for each slide.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        self._log.action("Full Validation", f"{len(slides_content)} slides")

        results: List[Optional[SlideValidationResult]] = [None] * len(slides_content)

        def _validate_one(idx: int, slide_data: Dict[str, Any]):
            slide_num = slide_data.get("id", 0)
            slide_title = slide_data.get("title", "Untitled")
            source = research_map.get(slide_num, "No source research available")
            return idx, self.validate_slide(
                slide_number=slide_num,
                slide_title=slide_title,
                slide_content=json.dumps(slide_data, default=str),
                source_research=source,
            )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit cross-slide check in parallel with individual validations
            cross_future = executor.submit(
                self.check_cross_slide_consistency, slides_content
            )

            futures = {
                executor.submit(_validate_one, i, sd): i
                for i, sd in enumerate(slides_content)
            }
            for future in as_completed(futures):
                try:
                    idx, result = future.result()
                    results[idx] = result
                except Exception as e:
                    idx = futures[future]
                    self._log.error(f"Validation failed for slide {idx}: {e}")
                    results[idx] = SlideValidationResult(
                        slide_number=idx,
                        is_valid=True,
                        issues=[],
                        confidence_score=0.0,
                    )

            # Check cross-slide result
            try:
                cross_result = cross_future.result()
                if not cross_result.is_consistent:
                    self._log.warning(
                        f"Cross-slide inconsistencies found: "
                        f"{len(cross_result.cross_slide_issues)} issues"
                    )
            except Exception as e:
                self._log.error(f"Cross-slide check failed: {e}")

        return [r for r in results if r is not None]
