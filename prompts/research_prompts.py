"""
prompts/research_prompts.py — Prompt templates for Research & Deep Research agents.
"""

from config import CURRENT_DATE_STR, CURRENT_YEAR

_DATA_RANGE = f"{CURRENT_YEAR - 2}-{CURRENT_YEAR}"

# ── Topic Decomposition ────────────────────────────────────
TOPIC_DECOMPOSITION_PROMPT = """You are a senior financial research analyst. Given the following presentation topic, decompose it into {num_subtopics} distinct, non-overlapping subtopics that would form a comprehensive research base for a professional presentation.

**Current Date:** """ + CURRENT_DATE_STR + """
**Topic:** {topic}
{focus_instruction}

**Requirements:**
- Each subtopic should cover a unique angle (e.g., market size, competitive landscape, trends, risks, opportunities).
- Subtopics must be specific enough to search for concrete data.
- Order subtopics from foundational context to forward-looking insights.
- All search queries should target recent data (""" + _DATA_RANGE + """).

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

**Current Date:** """ + CURRENT_DATE_STR + """
**Slide Title:** {slide_title}
**Required Data Type:** {data_type}
**Key Insight Needed:** {key_insight}
**Existing Context:** {existing_context}

**Instructions:**
- Find concrete numbers, percentages, dates, and statistics.
- If the data involves a chart, provide exact data points suitable for visualization.
- All data must be from """ + _DATA_RANGE + """ unless historical comparison is required.
- "Last 2 years" means """ + str(CURRENT_YEAR - 2) + """ to """ + str(CURRENT_YEAR) + """. "Recent" means """ + str(CURRENT_YEAR - 1) + """-""" + str(CURRENT_YEAR) + """.
- Cite specific sources for every data point.

Provide your findings as detailed, factual prose with inline citations.
"""

# ── Research Synthesis ──────────────────────────────────────
RESEARCH_SYNTHESIS_PROMPT = """You are a senior analyst synthesizing research findings into a coherent narrative.

**Current Date:** """ + CURRENT_DATE_STR + """
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
