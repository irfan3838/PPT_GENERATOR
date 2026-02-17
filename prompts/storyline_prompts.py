"""
prompts/storyline_prompts.py — Prompt templates for Framework Selection & Storyline agents.
"""

from config import CURRENT_DATE_STR, CURRENT_YEAR

# ── Framework Selection ─────────────────────────────────────
FRAMEWORK_SELECTION_PROMPT = """You are a presentation strategy expert. Analyze the topic and research context below, then select the **Top 2** most effective presentation frameworks from the library.

**Current Date:** """ + CURRENT_DATE_STR + """

**Topic:** {topic}
**Research Summary:** {research_summary}
**Target Audience:** {audience}

**Framework Library:**
1. **Pyramid Principle** — Top-down: conclusion first, then supporting arguments. Best for executive audiences.
2. **Hero's Journey** — Narrative arc: challenge → struggle → transformation. Best for storytelling.
3. **SCQA** (Situation-Complication-Question-Answer) — Problem-solving structure. Best for strategic recommendations.
4. **PAS** (Problem-Agitate-Solution) — Emotional urgency. Best for sales/persuasion.
5. **StoryBrand** — Audience as hero, presenter as guide. Best for client-facing.
6. **Sparkline** — Alternates between "what is" and "what could be." Best for visionary topics.
7. **Rule of Three** — Three core pillars structure. Best for balanced, memorable presentations.

**Output Format (JSON):**
{{
    "selections": [
        {{
            "framework": "Framework Name",
            "rank": 1,
            "reason": "Why this framework fits the topic and audience",
            "narrative_angle": "The specific angle/hook this framework would use"
        }},
        {{
            "framework": "Framework Name",
            "rank": 2,
            "reason": "Why this is the second-best choice",
            "narrative_angle": "The specific angle/hook this framework would use"
        }}
    ]
}}
"""

# ── Storyline Generation ────────────────────────────────────
STORYLINE_GENERATION_PROMPT = """You are a presentation architect. Create a detailed slide-by-slide outline for a professional financial presentation.

**Current Date:** """ + CURRENT_DATE_STR + """
**Important:** We are in the year """ + str(CURRENT_YEAR) + """. "Last 2 years" means """ + str(CURRENT_YEAR - 2) + """ to """ + str(CURRENT_YEAR) + """. "Recent" means """ + str(CURRENT_YEAR - 1) + """-""" + str(CURRENT_YEAR) + """.

**Topic:** {topic}
**Framework:** {framework_name} — {framework_description}
**Narrative Angle:** {narrative_angle}
**Research Findings:** {research_summary}
**Target Slide Count:** {slide_count} (you MUST generate EXACTLY {slide_count} slides — no more, no less)

**MANDATORY SLIDE STRUCTURE:**
You MUST include ALL of these special slides:
1. **Slide 1 — Title Slide** (layout_type: "title", visual_type: "none")
   - The very first slide. Contains presentation title and subtitle. NOTHING else.
2. **Slide 2 — Executive Summary** (layout_type: "exec_summary", visual_type: "none")
   - A high-level overview of the entire presentation. Key takeaways upfront.
3. **Slides 3 to {slide_count_minus_1} — Content Slides** (use various layout_types)
   - Mix of charts, infographics, tables, split layouts, bullet points.
   - At least 2-3 slides must be "chart" type with data visualizations.
   - At least 2-3 slides should be "bullet" type with visual_type "text_heavy_infographic" for eye-catching AI-generated infographic slides.
   - Use "split" layout for slides that combine text + visual.
4. **Slide {slide_count} — Thank You / Closing** (layout_type: "closing", visual_type: "none")
   - The very last slide. Contains closing message, thank you, call to action.

**Rules:**
- Generate EXACTLY {slide_count} slides. Count them carefully.
- Slide IDs must be sequential: 1, 2, 3, ..., {slide_count}.
- Every content slide must have a clear "so what" insight.
- Balance data-heavy slides (charts/tables) with text-heavy slides (infographics).
- For text-heavy slides, set visual_type to "text_heavy_infographic" — these will be rendered as beautiful AI-generated infographic images.
- For data slides, use appropriate chart types (bar_chart, line_chart, pie_chart, grouped_bar_chart).

**Output Format (JSON):**
{{
    "framework_name": "{framework_name}",
    "theme": "A one-line thematic thread for the deck",
    "slides": [
        {{
            "id": 1,
            "title": "Slide Title",
            "layout_type": "title|bullet|chart|table|split|exec_summary|section_divider|closing",
            "visual_type": "bar_chart|line_chart|pie_chart|grouped_bar_chart|dual_bar_comparison|multi_chart|transition_chart|text_heavy_infographic|split_visual_text|info_dashboard|table|none",
            "key_insight": "The 'so what' of this slide",
            "content_bullets": ["Bullet 1", "Bullet 2"],
            "data_source_query": "Search query to find data for this slide (empty if text-only)",
            "status": "planned"
        }}
    ]
}}
"""

# ── Comparative Outline ─────────────────────────────────────
COMPARATIVE_STORYLINE_PROMPT = """You are generating **two** side-by-side presentation outlines for the user to choose from.

**Current Date:** """ + CURRENT_DATE_STR + """
**Important:** We are in the year """ + str(CURRENT_YEAR) + """. "Last 2 years" means """ + str(CURRENT_YEAR - 2) + """ to """ + str(CURRENT_YEAR) + """. "Recent" means """ + str(CURRENT_YEAR - 1) + """-""" + str(CURRENT_YEAR) + """.

**Topic:** {topic}
**Research Summary:** {research_summary}
**Target Slide Count:** {target_slides} (EACH outline MUST have EXACTLY {target_slides} slides — no more, no less)

**Outline A — Framework: {framework_a}**
Angle: {angle_a}

**Outline B — Framework: {framework_b}**
Angle: {angle_b}

**MANDATORY SLIDE STRUCTURE (for BOTH outlines):**
1. **Slide 1 — Title Slide** (layout_type: "title", visual_type: "none")
   - Presentation title and subtitle only.
2. **Slide 2 — Executive Summary** (layout_type: "exec_summary", visual_type: "none")
   - High-level overview of the entire presentation.
3. **Slides 3 to {target_slides_minus_1} — Content Slides** (mixed layout_types)
   - At least 2-3 "chart" slides with data visualizations (bar_chart, line_chart, pie_chart, etc.)
   - At least 2-3 "bullet" slides with visual_type "text_heavy_infographic" for AI-generated infographic images
   - Use "split" for slides that combine text + visuals
   - Every slide must have a clear "so what" insight
4. **Slide {target_slides} — Thank You / Closing** (layout_type: "closing", visual_type: "none")
   - Closing message, thank you, call to action.

**CRITICAL:** Each outline must have EXACTLY {target_slides} slides with IDs 1 through {target_slides}.

For each outline, generate a complete slide-by-slide plan with these fields per slide:
- id (sequential integer)
- title
- layout_type: "title|bullet|chart|table|split|exec_summary|section_divider|closing"
- visual_type: "bar_chart|line_chart|pie_chart|grouped_bar_chart|dual_bar_comparison|multi_chart|transition_chart|text_heavy_infographic|split_visual_text|info_dashboard|table|none"
- key_insight
- content_bullets (list of strings)
- data_source_query
- status: "planned"

**Output Format (JSON):**
{{
    "outline_a": {{
        "framework_name": "{framework_a}",
        "theme": "...",
        "slides": [... EXACTLY {target_slides} slide objects ...]
    }},
    "outline_b": {{
        "framework_name": "{framework_b}",
        "theme": "...",
        "slides": [... EXACTLY {target_slides} slide objects ...]
    }}
}}
"""
