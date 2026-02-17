"""
agents/research_agent.py — Topic decomposition and grounded research agent.
Decomposes a topic into subtopics, then performs concurrent grounded searches.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from config import Settings, get_settings
from engine.llm_provider import LLMProvider
from engine.pipeline_logger import PipelineLogger
from engine.research_engine import GroundedResearchEngine
from models import ResearchFinding
from prompts.research_prompts import (
    RESEARCH_SYNTHESIS_PROMPT,
    TOPIC_DECOMPOSITION_PROMPT,
)


class SubtopicItem(BaseModel):
    title: str
    search_query: str
    data_type: str


class DecompositionResult(BaseModel):
    subtopics: List[SubtopicItem]


class ResearchAgent:
    """Decomposes topics into subtopics and performs grounded research."""

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
        self._log = PipelineLogger("ResearchAgent")

    def decompose_topic(
        self,
        topic: str,
        num_subtopics: int = 6,
        focus_areas: Optional[List[str]] = None,
    ) -> List[SubtopicItem]:
        """Break a broad topic into searchable subtopics.

        Args:
            topic: The main presentation topic.
            num_subtopics: Target number of subtopics.
            focus_areas: Optional list of priority subtopics.

        Returns:
            List of SubtopicItem with title, search_query, and data_type.
        """
        self._log.action("Decompose Topic", f"topic={topic[:60]}")

        focus_instruction = ""
        if focus_areas:
            bullet_list = "\n".join(f"- {area}" for area in focus_areas)
            focus_instruction = (
                f"\n**Critical Subtopics:**\n"
                f"Ensure the following specific areas are included and prioritized:\n"
                f"{bullet_list}\n"
            )

        prompt = TOPIC_DECOMPOSITION_PROMPT.format(
            topic=topic,
            num_subtopics=num_subtopics,
            focus_instruction=focus_instruction,
        )

        result = self._llm.generate_structured(
            prompt=prompt,
            response_model=DecompositionResult,
            system_instruction=(
                "You are a financial research analyst. "
                "Always respond with valid JSON matching the schema."
            ),
        )

        self._log.info(f"Decomposed into {len(result.subtopics)} subtopics")
        return result.subtopics

    def research_topic(
        self,
        topic: str,
        num_subtopics: int = 6,
        max_workers: int = 3,
        focus_areas: Optional[List[str]] = None,
    ) -> List[ResearchFinding]:
        """Full research pipeline: decompose → search → collect.

        Args:
            topic: The main presentation topic.
            num_subtopics: Number of subtopics to research.
            max_workers: Concurrent search threads.
            focus_areas: Specific subtopics to prioritize.

        Returns:
            List of ResearchFinding objects with sourced content.
        """
        with self._log.step_start("Full Topic Research"):
            # Step 1: Decompose
            subtopics = self.decompose_topic(
                topic=topic,
                num_subtopics=num_subtopics,
                focus_areas=focus_areas,
            )

            # Step 2: Concurrent search
            queries = [st.search_query for st in subtopics]
            self._log.action("Batch Search", f"{len(queries)} queries")
            findings = self._engine.search_multiple(
                queries=queries,
                context=f"Financial research on: {topic}",
                max_workers=max_workers,
            )

            # Step 3: Enrich findings with subtopic titles
            for finding, subtopic in zip(findings, subtopics):
                finding.topic = subtopic.title

            self._log.info(
                f"Research complete: {len(findings)} findings, "
                f"avg confidence={sum(f.confidence for f in findings) / max(len(findings), 1):.2f}"
            )

        return findings

    def synthesize(self, topic: str, findings: List[ResearchFinding]) -> str:
        """Synthesize multiple research findings into a coherent summary.

        Args:
            topic: The original topic.
            findings: List of ResearchFinding objects.

        Returns:
            A synthesized narrative string.
        """
        self._log.action("Synthesize Research", f"{len(findings)} findings")

        findings_text = "\n\n".join(
            f"### {f.topic}\n{f.content}\nSources: {', '.join(f.sources)}"
            for f in findings
        )

        prompt = RESEARCH_SYNTHESIS_PROMPT.format(
            topic=topic,
            findings_text=findings_text,
        )

        return self._llm.generate(
            prompt=prompt,
            system_instruction="You are a senior financial analyst creating a research synthesis.",
        )
