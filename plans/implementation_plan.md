# Finance Research Agent — Detailed Implementation Plan

## 1. Project Goal
Build an AI-powered presentation generator that creates professional PowerPoint decks from financial research topics. The system uses grounded search (Gemini) to ensure data accuracy and follows a multi-agent workflow for research, planning, validation, and content generation.

**Core Philosophy:**
- **Zero Hallucination:** Every number is backed by a verifiable source.
- **Deep Research:** Multi-step research process (broad topic → subtopics → slide-specific).
- **Human-in-the-Loop:** Explicit approval steps for critical content.
- **Visual Excellence:** Professional design using `python-pptx` with optional `Nano Banana Pro` enhancements.

---

## 2. Directory Structure

```
PPT_Builder_v1/
├── app.py                      # Main Streamlit application
├── config.py                   # Configuration (API keys, constants)
├── orchestrator.py             # Pipeline controller
├── agents/                     # Agent implementations
│   ├── __init__.py
│   ├── research_agent.py       # Topic & Subtopic research
│   ├── storyline_agent.py      # Narrative flow planning
│   ├── deep_research_agent.py  # Slide-specific research
│   ├── layout_decider.py       # Visual type selection
│   ├── slide_content_agent.py  # Content generation
│   ├── infographic_agent.py    # Infographic decision & prompt generation
│   └── critic_agent.py         # Data validation & consistency
├── engine/                     # Core logic & utilities
│   ├── __init__.py
│   ├── llm_provider.py         # Gemini API wrapper
│   ├── research_engine.py      # Search tool integration
│   ├── pipeline_logger.py      # Audit logging
│   └── vision_extractor.py     # Chart image analysis (optional)
├── generators/                 # Output generation
│   ├── __init__.py
│   ├── ppt_generator.py        # python-pptx builder
│   ├── chart_annotator.py      # Matplotlib chart generation
│   ├── table_generator.py      # Data table formatting
│   ├── exec_summary_builder.py # Specialized slide layouts
│   └── nano_banana_pro.py      # Optional visual enhancements
├── prompts/                    # LLM Prompt Templates
│   ├── __init__.py
│   ├── research_prompts.py
│   ├── storyline_prompts.py
│   ├── content_prompts.py
│   ├── infographic_prompts.py  # User-defined infographic templates
│   └── critic_prompts.py
├── data/                       # Local data storage
│   ├── output/                 # Generated PPTX files
│   ├── logs/                   # Pipeline execution logs
│   └── cache/                  # Research cache
├── plans/                      # Project plans & documentation
└── tasks/                      # Implementation checklists
```

---

## 3. Implementation Workflow

### Phase 1: Infrastructure Setup
1.  **Environment:** Set up Python virtual environment and install dependencies (`google-genai`, `python-pptx`, `streamlit`, `matplotlib`, `pandas`, `pydantic`).
2.  **Configuration:** Create `config.py` handling API keys, model selection (`gemini-2.0-flash` for speed, `gemini-1.5-pro` for reasoning), and retry logic.
3.  **LLM Wrapper:** Implement `LLMProvider` in `engine/llm_provider.py` to handle Gemini API calls with structured output and grounding toggles.
4.  **Logging:** Implement `PipelineLogger` to track agent actions, decisions, and errors.

### Phase 2: Core Research Engine
1.  **Research Engine:** Build `engine/research_engine.py` to interface with Gemini's grounded search capabilities. This is the source of truth for all data.
2.  **Research Agent:** Implement `agents/research_agent.py` to decompose the main topic into subtopics and execute concurrent searches.
    *   *Input:* Topic string.
    *   *Output:* List of `ResearchFinding` objects (content + source URLs).

### Phase 3: Storyline & Planning (Enhanced)
1.  **Deep Research & Framework Selection (Parallel):**
    *   **Deep Research:** `agents/deep_research_agent.py` uses Google Grounding to gather extensive context on the user's prompt.
    *   **Framework Selector:** `agents/framework_selector.py` analyzes the prompt and selects the **Top 2** best-fit frameworks from the library (Pyramid, Hero's Journey, SCQA, PAS, StoryBrand, Sparkline, Rule of Three).
2.  **Comparative Generation:** `agents/storyline_agent.py` generates two distinct narrative outlines (one for each selected framework) side-by-side.
    *   *Format:* slide-by-slide outline, visual direction, and technical precision.
3.  **User Selection:** User chooses the preferred storyline.
4.  **Finalization:** The selected outline becomes the blueprint for the `SlideContentAgent`.
5.  **Layout Decider:** Implemented as before to confirm visual types for the selected plan.

### Phase 4: Content Generation Loop
For each slide in the plan:
1.  **Deep Research:** Implement `agents/deep_research_agent.py` to perform targeted searches for missing specific data points required for charts/tables.
2.  **Content Generation:** Implement `agents/slide_content_agent.py` to synthesize research into final slide content (Title, Bullets, Chart Data, Insight).
    *   *Constraint:* Must interpret chart data into structured formats (JSON/Dict) for rendering.
3.  **Critic & Validation:** Implement `agents/critic_agent.py` to:
    *   Verify data consistency (e.g., bar chart totals match summary text).
    *   Check for hallucinations (compare against source text).
    *   Audit cross-slide consistency (e.g., "Revenue 2025" should be same on Slide 4 and Slide 8).

### Phase 4.5: Infographic Enrichment
1.  **Infographic Agent:** Implement `agents/infographic_agent.py` to analyze the generated slide content.
    *   *Logic:* Apply decision rules (e.g., >3 data points, process steps) to recommend infographics.
    *   *Output:* `InfographicPlan` containing type, placement, reasoning, and a specific generative prompt.
    *   *Prompting:* Must generate detailed, style-aware prompts for an image generation model (e.g., "Design a flow-style infographic...").

### Phase 5: PPTX Generation Engine
1.  **Base Generator:** Implement `generators/ppt_generator.py` using `python-pptx`.
    *   Define master layouts (Title, Content, Comparision, Blank).
    *   Implement shape placement logic (TextBox, Title, Footer).
2.  **Chart Engine:** Implement `generators/chart_annotator.py` using `matplotlib` to generate static chart images (high-DPI PNGs) that are embedded into slides. This ensures exact visual control.
3.  **Specialized Layouts:** Implement `generators/exec_summary_builder.py` for complex slides like the "Executive Summary" (grid of cards).

### Phase 6: Nano Banana Pro Integration (Optional)
1.  **Module Creation:** Create `generators/nano_banana_pro.py` as a distinct module.
    *   *Role:* Generate high-quality decorative assets options or advanced visualizations.
    *   *Integration:* Called by `ppt_generator.py` if the "Enhanced Visuals" toggle is active.
    *   *Fallback:* System must fully function without this module using standard shapes/charts.

### Phase 7: Orchestration & UI
1.  **Pipeline:** Build `orchestrator.py` to manage the state machine: `Idle -> Researching -> Planning -> Generatng -> Review -> Finalizing`.
2.  **Streamlit App:** Build `app.py` with:
    *   Sidebar for configuration (Topic, Subtopics, Template).
    *   Main review interface for strictly approving/editing slide plans before generation.
    *   Progress tracking for the generation pipeline.
    *   Download button for final PPTX / Log / Assets.

---

## 4. Key Data Structures (Draft)

**ResearchFinding:**
```python
class ResearchFinding(BaseModel):
    topic: str
    content: str
    sources: List[str]
    confidence: float
```

**SlidePlan:**
```python
class SlidePlan(BaseModel):
    id: int
    title: str
    layout_type: str  # 'bullet', 'chart', 'table', 'split'
    visual_type: str  # 'bar_chart', 'line_chart', 'none'
    key_insight: str
    content_bullets: List[str]
    data_source_query: str
    status: str       # 'planned', 'researched', 'generated', 'approved'
```

**ChartData:**
```python
class ChartData(BaseModel):
    title: str
    chart_type: str
    labels: List[str]
    datasets: List[Dict[str, Any]]  # label, data[], color
    x_axis_label: str
    y_axis_label: str

**InfographicProposal:**
```python
class InfographicProposal(BaseModel):
    slide_number: int
    slide_title: str
    infographic_recommended: bool
    infographic_type: str  # 'Data-Driven', 'Process', 'Comparison', etc.
    placement: str         # 'full-slide', 'right-column', 'bottom-section'
    reason: str
    generated_prompt: str
```



---

## 5. Dependencies
- **Core:** `python-pptx`, `pandas`, `pydantic`, `python-dotenv`
- **AI/LLM:** `google-genai` (Official Gemini SDK)
- **Web/UI:** `streamlit`
- **Visualization:** `matplotlib`, `seaborn`
- **Utils:** `loguru` (logging), `tenacity` (retries)

## 6. Execution Strategy
1.  **Prototype Research:** Get the grounded search working reliably first.
2.  **Skeleton Generator:** Build a "Hello World" PPTX generator that takes a rigid JSON and outputs a file.
3.  **Connect Logic:** Hook up the LLM to output that specific JSON structure.
## 7. Development Strategy: Claude Agent Teams
This project implementation will leverage **Claude Agent Teams** to develop modules in parallel, ensuring high code quality and specialized focus.

### 7.1 Team Roles & Responsibilities

| Role | Agent Name | Primary Focus | Key Tasks |
| :--- | :--- | :--- | :--- |
| **Team Lead** | `lead` | Orchestration & Synthesis | Defines architecture, assigns tasks to underlying agents, reviews code, merges PRs. |
| **Infrastructure Engineer** | `infra-agent` | Core Systems | Builds `config.py`, `llm_provider.py`, `pipeline_logger.py`, `research_engine.py`. Ensures strict typing and error handling. |
| **Agent Specialist** | `agent-dev` | AI Logic | Implements `ResearchAgent`, `StorylineAgent`, `CriticAgent`, `InfographicAgent`. Focuses on prompt engineering and structured outputs. |
| **Presentation Architect** | `pptx-dev` | Rendering Engine | Builds `ppt_generator.py`, `chart_annotator.py`, `exec_summary_builder.py`. Masters `python-pptx` and `matplotlib`. |
| **Frontend Developer** | `ui-dev` | User Experience | Builds `app.py` (Streamlit), state management, and the `PipelineOrchestrator` to connect UI to backend. |

### 7.2 Implementation Workflow
1.  **Lead Agent** initializes the repository and creates the skeleton directory structure.
2.  **Lead Agent** creates specific tasks for each specialist agent based on the Implementation Checklist.
3.  **Parallel Execution:**
    *   `infra-agent` builds the core engine.
    *   `agent-dev` starts implementing the Research and Storyline agents (using mocks for the engine initially if needed).
    *   `pptx-dev` creates the base PPTX template and chart generation logic.
4.  **Integration:** `ui-dev` connects the independent modules into `orchestrator.py` and `app.py`.
5.  **Review:** `lead` agent reviews the codebase for consistency (e.g., variable naming, typing) and runs integration tests.

### 7.3 Communication Protocol
*   **Context Sharing:** All agents share `plan/implementation_plan.md` and `config.py` as the source of truth.
*   **Mock-First Development:** Agents will mock dependencies (e.g., `ResearchAgent` mocks `LLMProvider`) to allow parallel work without blocking.
*   **Verification:** Each agent must include unit tests (`tests/`) for their module before marking a task as complete.

