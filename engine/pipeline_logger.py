"""
engine/pipeline_logger.py — Structured audit logging for the pipeline.
Uses loguru for structured, agent-scoped logging.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from config import LOG_DIR


class PipelineLogger:
    """Structured logger scoped to a specific pipeline agent or module."""

    _initialized: bool = False

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name
        self._ensure_global_setup()

    @classmethod
    def _ensure_global_setup(cls) -> None:
        """Configure loguru sinks once (idempotent)."""
        if cls._initialized:
            return

        # Remove default stderr sink
        logger.remove()

        # Console sink — human-readable
        logger.add(
            sys.stderr,
            format=(
                "<green>{time:HH:mm:ss}</green> | "
                "<level>{level:<8}</level> | "
                "<cyan>{extra[agent]:<20}</cyan> | "
                "{message}"
            ),
            level="INFO",
            colorize=True,
        )

        # File sink — structured JSON for audit
        logger.add(
            str(LOG_DIR / "pipeline_{time:YYYY-MM-DD}.log"),
            format="{time:YYYY-MM-DDTHH:mm:ss.SSS} | {level} | {extra[agent]} | {message}",
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            encoding="utf-8",
        )

        cls._initialized = True

    def _log(self, level: str, message: str, **kwargs: Any) -> None:
        """Internal log dispatch with agent context."""
        bound = logger.bind(agent=self.agent_name)
        getattr(bound, level)(message, **kwargs)

    # ── Public API ──────────────────────────────────────────

    def info(self, message: str, **kwargs: Any) -> None:
        self._log("info", message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        self._log("debug", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._log("warning", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._log("error", message, **kwargs)

    def action(self, action: str, detail: str = "") -> None:
        """Log an agent action (e.g., 'Calling LLM', 'Parsing JSON')."""
        msg = f"ACTION: {action}"
        if detail:
            msg += f" | {detail}"
        self._log("info", msg)

    def decision(self, decision: str, reason: str = "") -> None:
        """Log an agent decision point."""
        msg = f"DECISION: {decision}"
        if reason:
            msg += f" | Reason: {reason}"
        self._log("info", msg)

    def step_start(self, step_name: str) -> _StepTimer:
        """Start a timed step — returns a context manager."""
        return _StepTimer(self, step_name)


class _StepTimer:
    """Context manager for timing pipeline steps."""

    def __init__(self, log: PipelineLogger, step_name: str) -> None:
        self._log = log
        self._step = step_name
        self._start: float = 0.0

    def __enter__(self) -> _StepTimer:
        self._start = time.perf_counter()
        self._log.info(f"STEP START: {self._step}")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        elapsed = time.perf_counter() - self._start
        if exc_type is None:
            self._log.info(f"STEP DONE: {self._step} ({elapsed:.2f}s)")
        else:
            self._log.error(f"STEP FAILED: {self._step} ({elapsed:.2f}s) | {exc_val}")
