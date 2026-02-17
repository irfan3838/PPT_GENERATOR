"""
agents/storyline_agent.py — Framework selection, storyline generation, and comparative outlines.
Handles the narrative planning phase of the pipeline.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from config import Settings, get_settings
from engine.llm_provider import LLMProvider
from engine.pipeline_logger import PipelineLogger
from models import SlidePlan, StorylineOutline
from prompts.storyline_prompts import (
    COMPARATIVE_STORYLINE_PROMPT,
    FRAMEWORK_SELECTION_PROMPT,
    STORYLINE_GENERATION_PROMPT,
)


# ── Response Models for Structured Output ──────────────────

class FrameworkChoice(BaseModel):
    framework: str
    rank: int
    reason: str
    narrative_angle: str


class FrameworkSelectionResult(BaseModel):
    selections: List[FrameworkChoice]


class ComparativeResult(BaseModel):
    outline_a: StorylineOutline
    outline_b: StorylineOutline


# ── Framework Descriptions (for prompt injection) ──────────

FRAMEWORK_DESCRIPTIONS: Dict[str, str] = {
    "Pyramid Principle": "Top-down: conclusion first, then supporting arguments. Best for executive audiences.",
    "Hero's Journey": "Narrative arc: challenge → struggle → transformation. Best for storytelling.",
    "SCQA": "Situation-Complication-Question-Answer. Best for strategic recommendations.",
    "PAS": "Problem-Agitate-Solution. Best for sales/persuasion.",
    "StoryBrand": "Audience as hero, presenter as guide. Best for client-facing.",
    "Sparkline": "Alternates between 'what is' and 'what could be'. Best for visionary topics.",
    "Rule of Three": "Three core pillars structure. Best for balanced, memorable presentations.",
}


# ── Agents ──────────────────────────────────────────────────

class FrameworkSelectorAgent:
    """Selects the top 2 most effective frameworks for a given topic."""

    def __init__(
        self,
        llm: Optional[LLMProvider] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._llm = llm or LLMProvider(self._settings)
        self._log = PipelineLogger("FrameworkSelector")

    def select(
        self,
        topic: str,
        research_summary: str,
        audience: str = "business executives",
    ) -> List[FrameworkChoice]:
        """Select top 2 frameworks from the library of 7.

        Args:
            topic: Presentation topic.
            research_summary: Summary of research findings.
            audience: Target audience description.

        Returns:
            List of 2 FrameworkChoice objects ranked by fit.
        """
        self._log.action("Framework Selection", f"topic={topic[:60]}")

        prompt = FRAMEWORK_SELECTION_PROMPT.format(
            topic=topic,
            research_summary=research_summary[:3000],
            audience=audience,
        )

        result = self._llm.generate_structured(
            prompt=prompt,
            response_model=FrameworkSelectionResult,
            model=self._settings.gemini_pro_model,
            system_instruction="You are a presentation strategy expert. Respond with valid JSON.",
        )

        selections = sorted(result.selections, key=lambda x: x.rank)[:2]
        self._log.decision(
            f"Selected frameworks: {[s.framework for s in selections]}",
            reason=selections[0].reason if selections else "N/A",
        )
        return selections


class StorylineAgent:
    """Generates a slide-by-slide outline using a specific framework."""

    def __init__(
        self,
        llm: Optional[LLMProvider] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._llm = llm or LLMProvider(self._settings)
        self._log = PipelineLogger("StorylineAgent")

    def generate_outline(
        self,
        topic: str,
        framework_name: str,
        narrative_angle: str,
        research_summary: str,
        slide_count: int = 12,
    ) -> StorylineOutline:
        """Generate a full slide-by-slide outline.

        Args:
            topic: Presentation topic.
            framework_name: The framework to follow.
            narrative_angle: The specific hook/angle.
            research_summary: Summary of research findings.
            slide_count: Target number of slides.

        Returns:
            A StorylineOutline with framework, theme, and slides.
        """
        self._log.action(
            "Generate Outline",
            f"framework={framework_name}, slides={slide_count}",
        )

        framework_desc = FRAMEWORK_DESCRIPTIONS.get(framework_name, framework_name)

        prompt = STORYLINE_GENERATION_PROMPT.format(
            topic=topic,
            framework_name=framework_name,
            framework_description=framework_desc,
            narrative_angle=narrative_angle,
            research_summary=research_summary[:4000],
            slide_count=slide_count,
            slide_count_minus_1=slide_count - 1,
        )

        outline = self._llm.generate_structured(
            prompt=prompt,
            response_model=StorylineOutline,
            model=self._settings.gemini_pro_model,
            system_instruction=(
                "You are a presentation architect. Generate a complete, "
                "professional slide-by-slide outline. Respond with valid JSON."
            ),
        )

        self._log.info(
            f"Outline generated: {len(outline.slides)} slides, "
            f"framework={outline.framework_name}"
        )
        return outline


class ComparativeStorylineGenerator:
    """Generates two side-by-side outlines for user comparison."""

    def __init__(
        self,
        llm: Optional[LLMProvider] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._llm = llm or LLMProvider(self._settings)
        self._log = PipelineLogger("ComparativeStoryline")

    def generate(
        self,
        topic: str,
        research_summary: str,
        framework_a: str,
        angle_a: str,
        framework_b: str,
        angle_b: str,
        target_slides: int = 12,
    ) -> Tuple[StorylineOutline, StorylineOutline]:
        """Generate two competing outlines for user selection.

        Args:
            topic: Presentation topic.
            research_summary: Research context.
            framework_a / angle_a: First framework and its angle.
            framework_b / angle_b: Second framework and its angle.
            target_slides: Target number of slides per outline.

        Returns:
            Tuple of (outline_a, outline_b) StorylineOutline objects.
        """
        self._log.action(
            "Comparative Generation",
            f"{framework_a} vs {framework_b}, target={target_slides} slides",
        )

        prompt = COMPARATIVE_STORYLINE_PROMPT.format(
            topic=topic,
            research_summary=research_summary[:4000],
            framework_a=framework_a,
            angle_a=angle_a,
            framework_b=framework_b,
            angle_b=angle_b,
            target_slides=target_slides,
            target_slides_minus_1=target_slides - 1,
        )

        result = self._llm.generate_structured(
            prompt=prompt,
            response_model=ComparativeResult,
            model=self._settings.gemini_pro_model,
            system_instruction=(
                "You are generating two distinct presentation outlines. "
                "Each must be complete and self-contained. Respond with valid JSON."
            ),
        )

        self._log.info(
            f"Comparative outlines: A={len(result.outline_a.slides)} slides, "
            f"B={len(result.outline_b.slides)} slides"
        )
        return result.outline_a, result.outline_b
