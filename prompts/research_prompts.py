"""
prompts/research_prompts.py — Prompt templates for Research & Deep Research agents.
"""

# ── Topic Decomposition ────────────────────────────────────
TOPIC_DECOMPOSITION_PROMPT = """You are a senior financial research analyst. Given the following presentation topic, decompose it into {num_subtopics} distinct, non-overlapping subtopics that would form a comprehensive research base for a professional presentation.

**Topic:** {topic}
{focus_instruction}

**Requirements:**
- Each subtopic should cover a unique angle (e.g., market size, competitive landscape, trends, risks, opportunities).
- Subtopics must be specific enough to search for concrete data.
- Order subtopics from foundational context to forward-looking insights.

**Output Format (JSON):**
{{
    "subtopics": [
        {{
            "title": "Subtopic title",
            "search_query": "Optimized search query for grounded research",
            "data_type": "one of: statistics, trends, comparison, forecast, overview"
        }}
    ]
}}
"""

# ── Deep Research (Slide-Specific) ──────────────────────────
DEEP_RESEARCH_PROMPT = """You are a financial data specialist. You need to find **specific, verifiable data** for a presentation slide.

**Slide Title:** {slide_title}
**Required Data Type:** {data_type}
**Key Insight Needed:** {key_insight}
**Existing Context:** {existing_context}

**Instructions:**
- Find concrete numbers, percentages, dates, and statistics.
- If the data involves a chart, provide exact data points suitable for visualization.
- All data must be from 2023-2025 unless historical comparison is required.
- Cite specific sources for every data point.

Provide your findings as detailed, factual prose with inline citations.
"""

# ── Research Synthesis ──────────────────────────────────────
RESEARCH_SYNTHESIS_PROMPT = """You are a senior analyst synthesizing research findings into a coherent narrative.

**Topic:** {topic}
**Research Findings:**
{findings_text}

**Task:** Create a unified synthesis that:
1. Identifies the key themes across all findings.
2. Highlights the most impactful statistics and data points.
3. Notes any conflicting data and recommends which source to trust.
4. Suggests the strongest narrative angle for a presentation.

Respond in structured prose with clear section headers.
"""
