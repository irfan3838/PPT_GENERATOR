"""
prompts/infographic_prompts.py — Prompt templates for InfographicAgent.
"""

# ── Infographic Decision ────────────────────────────────────
INFOGRAPHIC_DECISION_PROMPT = """You are a visual design strategist. Analyze the slide content and decide whether an infographic would enhance comprehension.

**Slide #{slide_number}: {slide_title}**
**Layout Type:** {layout_type}
**Content:** {content_summary}
**Data Available:** {data_summary}

**Decision Rules:**
- If there are >3 comparable data points → Data-Driven infographic
- If content describes a process/workflow with steps → Process infographic
- If content compares 2-3 entities side by side → Comparison infographic
- If content shows evolution/milestones → Timeline infographic
- If content is purely textual with no data → NO infographic

**Output Format (JSON):**
{{
    "slide_number": {slide_number},
    "slide_title": "{slide_title}",
    "infographic_recommended": true/false,
    "infographic_type": "Data-Driven|Process|Comparison|Timeline|none",
    "placement": "full-slide|right-column|bottom-section",
    "reason": "Why this infographic type was chosen (or why none)",
    "generated_prompt": "If recommended: A detailed prompt for an image generation model to create this infographic. Include style, colors, layout description, and specific data to display. If not recommended: empty string."
}}
"""

# ── Infographic Style Guide ─────────────────────────────────
INFOGRAPHIC_STYLE_PROMPT = """Design specifications for generated infographics:

**Color Palette:** Professional financial — Navy (#1B2A4A), Steel Blue (#4A90D9), Teal (#2ECC71), Warm Gray (#95A5A6), Accent Orange (#E67E22)
**Typography Direction:** Clean, sans-serif, minimal text on infographic itself
**Layout:** Whitespace-rich, data-forward, no decorative clutter
**Style:** Flat design, subtle gradients, icon-driven where appropriate
**Dimensions:** {width}x{height} pixels at {dpi} DPI

The generated prompt should instruct the image model to produce an infographic that:
1. Uses the color palette above
2. Is readable at slide-projection size
3. Has a clear visual hierarchy
4. Includes a title and source annotation area
"""
