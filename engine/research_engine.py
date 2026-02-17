"""
engine/research_engine.py — Grounded search interface.
Wraps LLMProvider to provide structured research results with source verification.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from config import Settings, get_settings
from engine.llm_provider import LLMProvider
from engine.pipeline_logger import PipelineLogger
from models import ResearchFinding


class GroundedResearchEngine:
    """High-level research interface using Gemini grounded search."""

    def __init__(
        self,
        llm: Optional[LLMProvider] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._llm = llm or LLMProvider(self._settings)
        self._log = PipelineLogger("ResearchEngine")

    def search(self, query: str, context: str = "") -> ResearchFinding:
        """Execute a single grounded search and return a ResearchFinding.

        Args:
            query: The search query.
            context: Optional surrounding context for more targeted search.

        Returns:
            A ResearchFinding with content and source URLs.
        """
        system_instruction = (
            "You are a financial research analyst. Provide factual, data-driven "
            "answers with specific numbers, dates, and statistics. "
            "Always cite your sources. Be precise and concise."
        )
        if context:
            full_query = f"Context: {context}\n\nResearch Question: {query}"
        else:
            full_query = query

        self._log.action("Research Search", f"query={query[:80]}")

        result = self._llm.generate_with_search(
            query=full_query,
            system_instruction=system_instruction,
        )

        # Calculate confidence based on source availability
        sources = result.get("grounding_sources", [])
        text = result.get("text", "")
        confidence = self._estimate_confidence(text, sources)

        finding = ResearchFinding(
            topic=query,
            content=text,
            sources=sources,
            confidence=confidence,
        )

        self._log.info(
            f"Search complete: {len(sources)} sources, confidence={confidence:.2f}"
        )
        return finding

    def search_multiple(
        self,
        queries: List[str],
        context: str = "",
        max_workers: int = 3,
    ) -> List[ResearchFinding]:
        """Execute multiple searches concurrently.

        Args:
            queries: List of search queries.
            context: Shared context for all queries.
            max_workers: Max concurrent API calls.

        Returns:
            List of ResearchFinding objects (order matches input queries).
        """
        self._log.action(
            "Batch Research",
            f"{len(queries)} queries, max_workers={max_workers}",
        )

        results: List[Optional[ResearchFinding]] = [None] * len(queries)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(self.search, q, context): i
                for i, q in enumerate(queries)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    self._log.error(f"Search failed for query[{idx}]: {e}")
                    results[idx] = ResearchFinding(
                        topic=queries[idx],
                        content=f"Search failed: {e}",
                        sources=[],
                        confidence=0.0,
                    )

        # Filter out None values (shouldn't happen, but be safe)
        return [r for r in results if r is not None]

    @staticmethod
    def _estimate_confidence(text: str, sources: List[str]) -> float:
        """Heuristic confidence score based on response quality signals."""
        score = 0.0

        # Source count signal
        if len(sources) >= 3:
            score += 0.4
        elif len(sources) >= 1:
            score += 0.2

        # Content length signal (meaningful content)
        if len(text) > 500:
            score += 0.3
        elif len(text) > 200:
            score += 0.2
        elif len(text) > 50:
            score += 0.1

        # Presence of numbers (financial data signal)
        import re
        numbers = re.findall(r'\d+\.?\d*%?', text)
        if len(numbers) >= 3:
            score += 0.3
        elif len(numbers) >= 1:
            score += 0.15

        return min(score, 1.0)
