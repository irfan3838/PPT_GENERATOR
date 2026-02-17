"""
prompts/render_decision_prompts.py — Prompts for the Slide Render Deciding Agent.
"""

# Note: RENDER_DECISION_PROMPT is no longer used (deciding agent is deterministic),
# but kept for reference.
RENDER_DECISION_PROMPT = """You are a presentation design strategist. Analyze the slide below and decide the optimal rendering strategy.

**Slide Details:**
- Title: {slide_title}
- Layout: {layout_type}
- Visual Type: {visual_type}
- Key Insight: {key_insight}
- Content:
{content_bullets}
- Has Chart Data: {has_chart}
- Has Table Data: {has_table}

**Decision Criteria:**
- **image_generation**: Choose this for text-heavy slides with qualitative content, bullet points, insights, summaries, recommendations, or narrative information. These slides benefit from beautiful, professionally designed visual layouts with icons, color blocks, and infographic-style arrangements.
- **standard**: Choose this for data-heavy slides with charts, tables, numeric comparisons, or structured data that requires precise rendering.

**Rules:**
- If the slide has chart or table data, ALWAYS choose "standard".
- If the slide is primarily text, bullets, or qualitative insights, prefer "image_generation".
- Be bold — text-heavy slides look MUCH better as AI-generated images than plain bullet points.

**Output Format (JSON):**
{{
    "slide_id": 0,
    "render_mode": "image_generation|standard",
    "reason": "Brief explanation of why this rendering mode was chosen",
    "image_prompt": "",
    "confidence": 0.9
}}
"""

IMAGE_SLIDE_PROMPT_TEMPLATE = """Generate a SINGLE professional business presentation slide as a high-quality image.

═══════════════════════════════════════════
 SLIDE CONTENT — MUST APPEAR EXACTLY AS WRITTEN
═══════════════════════════════════════════

Title: {slide_title}

Key Points (include ALL of these on the slide):
{content_bullets}

Key Insight / Takeaway: {key_insight}

Additional Context: {speaker_notes}

═══════════════════════════════════════════
 VISUAL DESIGN SPECIFICATIONS
═══════════════════════════════════════════

DIMENSIONS: 16:9 widescreen landscape (1920×1080 pixels)

COLOR PALETTE:
  • Primary Color: {primary_color} (use for title, key headings, accent bars)
  • Accent Color: {accent_color} (use for highlights, callout boxes, icons, important numbers)
  • Background: {bg_color} or a very subtle gradient from {bg_color} to a slightly lighter shade
  • Body Text: {text_color}

TYPOGRAPHY:
  • Font Family: Calibri for ALL text elements
  • Title: 28-32pt bold, {primary_color}
  • Subtitles/Section Headers: 18-22pt semibold
  • Body Text: 14-16pt regular
  • Key numbers/stats: 36-48pt bold accent color

═══════════════════════════════════════════
 INFOGRAPHIC / LAYOUT STYLE
═══════════════════════════════════════════

Create an eye-catching INFOGRAPHIC-STYLE layout. Choose from these approaches:
  • Icon Grid: Use flat geometric icons with labels arranged in 2×2 or 3×2 grids
  • Process Flow: Connected steps with arrows showing progression
  • Highlight Cards: Colored cards/tiles with rounded corners, each containing a key point
  • Comparison Blocks: Side-by-side colored sections comparing concepts
  • Timeline / Roadmap: Horizontal or vertical timeline with milestone nodes
  • Statistics Dashboard: Large numbers with supporting context and accent-colored backgrounds
  • Hub-and-Spoke: Central concept connected to surrounding points
  • Pyramid / Stacked: Hierarchical arrangement of concepts

DESIGN PRINCIPLES:
  • Use geometric shapes (circles, rounded rectangles, hexagons) to organize information
  • Add subtle accent lines, dividers, or separator bars between sections
  • Use colored number callouts for statistics (large bold numbers in accent color)
  • Include small flat icons (arrows, lightbulbs, gears, charts, targets, shields) next to points
  • Create clear visual hierarchy — title → key insight → supporting points
  • Use whitespace generously — DO NOT overcrowd
  • High contrast — must be readable when projected on a large screen
  • Slide number {slide_num} of {total_slides} in small text at bottom-right corner

═══════════════════════════════════════════
 STRICT RULES
═══════════════════════════════════════════

ABSOLUTELY FORBIDDEN:
  ✗ NO human figures, people, faces, hands, or silhouettes
  ✗ NO cartoon characters or illustrated people
  ✗ NO clip art or stock photo style imagery
  ✗ NO 3D rendered objects or realistic photographs
  ✗ NO decorative borders or frames that waste space
  ✗ NO placeholder text — use ONLY the exact content provided above

REQUIRED:
  ✓ Every piece of text must be legible and correctly spelled
  ✓ All data, numbers, and facts must be EXACTLY as provided — do NOT invent figures
  ✓ The slide must look like it was designed by a top-tier consulting firm (McKinsey/BCG quality)
  ✓ Clean, modern, professional — suitable for C-suite business presentation
  ✓ The overall impression should be an eye-catching infographic, NOT a plain text slide
"""

SLIDE_REFINEMENT_PROMPT = """Refine and polish this presentation slide image. Make it visually stunning while keeping ALL content EXACTLY the same.

═══════════════════════════════════════════
 ABSOLUTE DATA PRESERVATION RULES
═══════════════════════════════════════════

THIS IS THE #1 PRIORITY — data integrity is non-negotiable:

  ✗ Do NOT alter, move, resize, or remove ANY bar chart, pie chart, line graph, or table
  ✗ Do NOT change any bar heights, pie slice sizes, line positions, or data point values
  ✗ Do NOT remove or reposition any axis labels, tick marks, legends, or data labels
  ✗ Do NOT change any numbers, percentages, or values shown anywhere on the slide
  ✗ Do NOT merge, split, or rearrange any table rows or columns
  ✗ Do NOT remove any annotations, callout arrows, or data-point labels
  ✗ Do NOT redraw or recreate any chart — the existing chart must remain pixel-accurate
  ✗ Do NOT add human figures, people, cartoons, or clip art

  The bar charts, pie charts, line graphs, grouped bar charts, stacked bar charts,
  and tables in this image must appear EXACTLY as shown — same bars, same values,
  same axes, same labels, same legend entries, same annotation text.
  If it has data, LEAVE THE DATA ALONE.

═══════════════════════════════════════════
 WHAT TO REFINE (visual polish only)
═══════════════════════════════════════════

  ✓ Apply this EXACT color theme to non-data elements:
      Primary: {primary_color} (title bar, headers, accent lines)
      Accent: {accent_color} (highlights, callout boxes, emphasis borders)
      Background: {bg_color} (overall slide background)
      Text: {text_color} (body text)
  ✓ Polish the SURROUNDINGS of charts/graphs:
      — Background behind the chart area
      — Border/frame around the chart
      — Title and subtitle styling above the chart
      — Source annotation below the chart
  ✓ Improve visual hierarchy — bolder titles, larger key numbers
  ✓ Add subtle professional touches: soft shadows on cards, refined borders, cleaner spacing
  ✓ Make tables more elegant — refined header styling, cleaner row separators (keep all cell values)
  ✓ Improve typography — consistent Calibri-like font sizing, better alignment
  ✓ Add subtle gradient or texture to backgrounds (keeping it professional)
  ✓ Ensure all annotations and callouts are crisp and readable
  ✓ Add accent bars or divider lines to separate sections
  ✓ Make the slide look like it was designed by McKinsey/BCG — top-tier consulting quality

═══════════════════════════════════════════
 SLIDE CONTEXT
═══════════════════════════════════════════

  Title: {slide_title}
  Type: {slide_type}
  Slide {slide_num} of {total_slides}

OUTPUT:
  16:9 widescreen landscape (1920×1080), high-resolution, presentation-ready.
  The refined slide must be immediately usable in a professional business presentation.
  ALL charts, graphs, and tables must be IDENTICAL to the input — only the surrounding design is polished.
"""

