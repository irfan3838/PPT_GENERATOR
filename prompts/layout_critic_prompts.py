"""
prompts/layout_critic_prompts.py — Prompt templates for LayoutCriticAgent.
"""

LAYOUT_QUALITY_PROMPT = """You are a presentation design quality assessor. Evaluate the visual layout of this slide.

**Slide #{slide_number}: {slide_title}**
**Layout Type:** {layout_type}
**Content Volume:** {num_bullets} bullet points, has_chart={has_chart}, has_table={has_table}, has_infographic={has_infographic}
**Key Insight Present:** {has_insight}

**Element Positions (inches from top-left, on a 13.333 x 7.5 inch slide):**
{element_positions}

**Evaluate:**
1. Is the content volume appropriate for the available space? (Too many bullets for area, chart too small, etc.)
2. Is there sufficient whitespace between elements for readability?
3. Would the audience be able to read all text at projection size?
4. Is the visual hierarchy clear (title > content > insight > footer)?

**Output Format (JSON):**
{{
    "quality_score": 0.0-1.0,
    "feedback": "Specific feedback on layout quality and any issues found",
    "density_warning": true/false
}}
"""
