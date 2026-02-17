"""
engine/llm_provider.py — Gemini API wrapper with grounding and structured output.
Uses google-genai SDK, tenacity for retries, and PipelineLogger for audit.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Type

from google import genai
from google.genai import types
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import Settings, get_settings
from engine.pipeline_logger import PipelineLogger


class LLMProvider:
    """Unified interface for Gemini API calls with grounding support."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._log = PipelineLogger("LLMProvider")
        self._client = genai.Client(api_key=self._settings.gemini_api_key)
        self._log.info("LLMProvider initialized")

    # ── Public API ──────────────────────────────────────────

    def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        use_grounding: bool = False,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        system_instruction: Optional[str] = None,
    ) -> str:
        """Generate a plain-text response from Gemini.

        Args:
            prompt: The user prompt.
            model: Override model name (defaults to flash model).
            use_grounding: Enable Google Search grounding.
            temperature: Sampling temperature override.
            max_output_tokens: Max output tokens override.
            system_instruction: System-level instruction.

        Returns:
            The model's text response.
        """
        model_name = model or self._settings.gemini_flash_model
        temp = temperature if temperature is not None else self._settings.llm_temperature
        max_tokens = max_output_tokens or self._settings.llm_max_output_tokens

        config = self._build_config(
            temperature=temp,
            max_output_tokens=max_tokens,
            use_grounding=use_grounding,
            system_instruction=system_instruction,
        )

        self._log.action(
            "LLM Call",
            f"model={model_name} grounding={use_grounding} temp={temp}",
        )

        response = self._call_api(model_name, prompt, config)
        text = response.text or ""
        self._log.debug(f"Response length: {len(text)} chars")
        return text

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[BaseModel],
        *,
        model: Optional[str] = None,
        use_grounding: bool = False,
        temperature: Optional[float] = None,
        system_instruction: Optional[str] = None,
    ) -> BaseModel:
        """Generate a response and parse it into a Pydantic model.

        Uses Gemini's JSON mode to get structured output, then validates
        via the provided Pydantic model.

        Args:
            prompt: The user prompt.
            response_model: Pydantic model class to parse the response into.
            model: Override model name.
            use_grounding: Enable Google Search grounding.
            temperature: Sampling temperature override.
            system_instruction: System-level instruction.

        Returns:
            A validated instance of response_model.
        """
        model_name = model or self._settings.gemini_flash_model
        temp = temperature if temperature is not None else self._settings.llm_temperature

        config = self._build_config(
            temperature=temp,
            max_output_tokens=self._settings.llm_max_output_tokens,
            use_grounding=use_grounding,
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_model,
        )

        self._log.action(
            "LLM Structured Call",
            f"model={model_name} schema={response_model.__name__}",
        )

        response = self._call_api(model_name, prompt, config)
        raw_text = response.text or "{}"

        # Parse and validate
        try:
            parsed = json.loads(raw_text)
            result = response_model.model_validate(parsed)
            self._log.debug(f"Parsed {response_model.__name__} successfully")
            return result
        except (json.JSONDecodeError, Exception) as e:
            self._log.error(f"Failed to parse structured output: {e}")
            raise ValueError(
                f"LLM returned invalid JSON for {response_model.__name__}: {e}"
            ) from e

    def generate_with_search(
        self,
        query: str,
        *,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a grounded response and extract search metadata.

        Returns a dict with 'text', 'grounding_sources', and 'search_queries'.
        """
        model_name = model or self._settings.gemini_flash_model

        config = self._build_config(
            temperature=0.2,
            max_output_tokens=self._settings.llm_max_output_tokens,
            use_grounding=True,
            system_instruction=system_instruction,
        )

        self._log.action("Grounded Search", f"query={query[:80]}...")
        response = self._call_api(model_name, query, config)

        # Extract grounding metadata
        sources: list[str] = []
        search_queries: list[str] = []
        if response.candidates:
            candidate = response.candidates[0]
            grounding_meta = getattr(candidate, "grounding_metadata", None)
            if grounding_meta:
                chunks = getattr(grounding_meta, "grounding_chunks", []) or []
                for chunk in chunks:
                    web = getattr(chunk, "web", None)
                    if web and hasattr(web, "uri"):
                        sources.append(web.uri)
                queries = getattr(grounding_meta, "web_search_queries", []) or []
                search_queries = list(queries)

        self._log.info(f"Grounded search returned {len(sources)} sources")
        return {
            "text": response.text or "",
            "grounding_sources": sources,
            "search_queries": search_queries,
        }

    @staticmethod
    def _sanitize_schema(schema: Dict[str, Any], defs: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Recursively sanitize a JSON schema for the Gemini API.

        Removes: additionalProperties, title, default, $defs
        Inlines: $ref references
        Converts: anyOf[Type, null] → Type with nullable marker
        """
        if defs is None:
            defs = schema.pop("$defs", {})

        if "$ref" in schema:
            ref_name = schema["$ref"].rsplit("/", 1)[-1]
            resolved = defs.get(ref_name, {})
            return LLMProvider._sanitize_schema(dict(resolved), defs)

        # Handle anyOf with null (Optional fields)
        if "anyOf" in schema:
            non_null = [s for s in schema["anyOf"] if s != {"type": "null"}]
            if len(non_null) == 1:
                result = LLMProvider._sanitize_schema(dict(non_null[0]), defs)
                result["nullable"] = True
                return result

        out: Dict[str, Any] = {}
        for key, value in schema.items():
            if key in ("additionalProperties", "title", "default", "$defs"):
                continue
            if key == "properties" and isinstance(value, dict):
                out[key] = {
                    k: LLMProvider._sanitize_schema(dict(v), defs)
                    for k, v in value.items()
                }
            elif key == "items" and isinstance(value, dict):
                out[key] = LLMProvider._sanitize_schema(dict(value), defs)
            else:
                out[key] = value
        return out

    def _build_config(
        self,
        temperature: float,
        max_output_tokens: int,
        use_grounding: bool = False,
        system_instruction: Optional[str] = None,
        response_mime_type: Optional[str] = None,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> types.GenerateContentConfig:
        """Build the Gemini GenerateContentConfig."""
        tools = []
        if use_grounding and self._settings.enable_grounding:
            tools.append(types.Tool(google_search=types.GoogleSearch()))

        kwargs: Dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }
        if tools:
            kwargs["tools"] = tools
        if system_instruction:
            kwargs["system_instruction"] = system_instruction
        if response_mime_type:
            kwargs["response_mime_type"] = response_mime_type
        if response_schema:
            kwargs["response_mime_type"] = response_mime_type or "application/json"
            # Sanitize schema to remove Gemini-incompatible keywords
            raw_schema = response_schema.model_json_schema()
            clean_schema = self._sanitize_schema(raw_schema)
            kwargs["response_schema"] = clean_schema

        return types.GenerateContentConfig(**kwargs)

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        reraise=True,
    )
    def _call_api(
        self,
        model_name: str,
        prompt: str,
        config: types.GenerateContentConfig,
    ) -> Any:
        """Execute the Gemini API call with retry logic."""
        return self._client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )
