"""
prompts/critic_prompts.py — Prompt templates for CriticAgent (validation & consistency).
"""

# ── Single Slide Validation ─────────────────────────────────
SLIDE_VALIDATION_PROMPT = """You are a rigorous data auditor reviewing a presentation slide for accuracy and consistency.

**Slide #{slide_number}: {slide_title}**

**Content:**
{slide_content}

**Source Research:**
{source_research}

**Validation Checks:**
1. **Data Accuracy:** Do all numbers match the source research? Flag any discrepancies.
2. **Internal Consistency:** Do chart totals match text claims? Do percentages add up?
3. **Hallucination Detection:** Is there any claim NOT supported by the source research?
4. **Completeness:** Is the key insight supported by the presented data?

**Output Format (JSON):**
{{
    "slide_number": {slide_number},
    "is_valid": true/false,
    "issues": [
        {{
            "type": "data_mismatch|hallucination|inconsistency|incomplete",
            "severity": "critical|warning|info",
            "description": "What is wrong",
            "suggestion": "How to fix it"
        }}
    ],
    "confidence_score": 0.0-1.0
}}
"""

# ── Cross-Slide Consistency ─────────────────────────────────
CROSS_SLIDE_CONSISTENCY_PROMPT = """You are a presentation consistency auditor. Check that data referenced across multiple slides is consistent.

**All Slides Content:**
{all_slides_json}

**Checks:**
1. If "Revenue 2025" appears on Slide 3 and Slide 8, the number must be identical.
2. Company names, dates, and acronyms must be consistent throughout.
3. The narrative flow must be logical (no contradictions between slides).
4. Visual styles referenced must be coherent.

**Output Format (JSON):**
{{
    "is_consistent": true/false,
    "cross_slide_issues": [
        {{
            "slides_affected": [3, 8],
            "type": "data_conflict|naming_inconsistency|narrative_gap",
            "description": "What is inconsistent",
            "recommendation": "How to resolve"
        }}
    ]
}}
"""
