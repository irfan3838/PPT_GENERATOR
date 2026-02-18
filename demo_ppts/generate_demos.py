"""
generate_demos.py — Generate / refresh demo PPTs using the engine.

Reads demo_config.json, runs each demo through the full pipeline,
saves the resulting PPTX files in demo_ppts/output/, and updates
demo_status.json with metadata (timestamps, file paths, etc.).

Can be run directly:  python demo_ppts/generate_demos.py
Or triggered weekly via the scheduler.
"""

from __future__ import annotations

import json
import shutil
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root is on the path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

DEMO_DIR = ROOT_DIR / "demo_ppts"
DEMO_OUTPUT_DIR = DEMO_DIR / "output"
DEMO_CONFIG_PATH = DEMO_DIR / "demo_config.json"
DEMO_STATUS_PATH = DEMO_DIR / "demo_status.json"

# Ensure output directory exists
DEMO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _load_config() -> dict:
    """Load the demo configuration."""
    with open(DEMO_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_status() -> dict:
    """Load the generation status (or create default)."""
    if DEMO_STATUS_PATH.exists():
        with open(DEMO_STATUS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"demos": {}, "last_full_run": None}


def _save_status(status: dict) -> None:
    """Persist generation status."""
    with open(DEMO_STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=4, default=str)


def needs_regeneration(status: dict, force: bool = False) -> bool:
    """Check if demos need regeneration (weekly cadence)."""
    if force:
        return True
    last_run = status.get("last_full_run")
    if not last_run:
        return True
    try:
        last_dt = datetime.fromisoformat(last_run)
        return (datetime.now() - last_dt) > timedelta(days=7)
    except (ValueError, TypeError):
        return True


def generate_single_demo(demo_cfg: dict, status: dict) -> dict:
    """Generate a single demo PPT using the pipeline.

    Returns metadata dict for the demo.
    """
    from orchestrator import PipelineOrchestrator

    demo_id = demo_cfg["id"]
    topic = demo_cfg["topic"]
    subtopics = demo_cfg.get("subtopics", [])
    audience = demo_cfg.get("audience", "business executives")
    num_subtopics = demo_cfg.get("num_subtopics", 6)
    target_slides = demo_cfg.get("target_slides", 12)

    print(f"\n{'='*60}")
    print(f"  Generating: {demo_cfg['title']}")
    print(f"  Topic:      {topic[:80]}...")
    print(f"{'='*60}")

    filename = f"demo_{demo_id}.pptx"
    output_path = DEMO_OUTPUT_DIR / filename

    try:
        orchestrator = PipelineOrchestrator()

        # Phase 1: Research
        print("  [1/6] Researching...")
        orchestrator.run_research(
            topic=topic,
            num_subtopics=num_subtopics,
            focus_subtopics=subtopics if subtopics else None,
        )

        # Phase 2: Framework selection + outlines
        print("  [2/6] Selecting frameworks...")
        orchestrator.run_framework_selection(audience)
        orchestrator.run_comparative_outlines(target_slides=target_slides)
        orchestrator.select_outline("a")  # Auto-pick option A

        # Phase 3: Content generation
        print("  [3/6] Generating content...")
        orchestrator.run_content_generation()

        # Phase 4: Render decisions + images
        print("  [4/6] Render decisions & image generation...")
        try:
            orchestrator.run_render_decisions()
            orchestrator.run_slide_image_generation()
        except Exception:
            print("  [4/6] Image generation skipped (non-critical)")

        # Phase 5: Infographics + refinement
        print("  [5/6] Infographic evaluation & refinement...")
        try:
            orchestrator.run_infographic_evaluation()
            orchestrator.run_infographic_generation()
            orchestrator.run_universal_refinement()
        except Exception:
            print("  [5/6] Refinement skipped (non-critical)")

        # Phase 6: Layout validation + PPTX
        print("  [6/6] Building PPTX...")
        try:
            orchestrator.run_layout_validation()
        except Exception:
            pass

        pptx_path = orchestrator.run_pptx_generation(output_filename=filename)

        # Copy to demo output directory
        if pptx_path.exists() and pptx_path != output_path:
            shutil.copy2(pptx_path, output_path)

        meta = {
            "id": demo_id,
            "title": demo_cfg["title"],
            "description": demo_cfg.get("description", ""),
            "topic": topic,
            "subtopics": subtopics,
            "audience": audience,
            "num_subtopics": num_subtopics,
            "target_slides": target_slides,
            "filename": filename,
            "file_path": str(output_path),
            "generated_at": datetime.now().isoformat(),
            "file_size_kb": round(output_path.stat().st_size / 1024, 1) if output_path.exists() else 0,
            "status": "success",
            "error": None,
        }

        print(f"  ✅ Done: {output_path.name} ({meta['file_size_kb']} KB)")
        return meta

    except Exception as e:
        print(f"  ❌ Failed: {e}")
        traceback.print_exc()
        return {
            "id": demo_id,
            "title": demo_cfg["title"],
            "description": demo_cfg.get("description", ""),
            "topic": topic,
            "subtopics": subtopics,
            "audience": audience,
            "filename": filename,
            "file_path": str(output_path),
            "generated_at": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


def generate_all_demos(force: bool = False) -> None:
    """Generate all demo PPTs if needed."""
    config = _load_config()
    status = _load_status()

    if not needs_regeneration(status, force=force):
        print("✅ Demos are up to date (generated within the last 7 days).")
        return

    print("\n" + "=" * 60)
    print("  PPT Builder — Demo Generation")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    for demo_cfg in config["demo_ppts"]:
        meta = generate_single_demo(demo_cfg, status)
        status["demos"][meta["id"]] = meta

    status["last_full_run"] = datetime.now().isoformat()
    _save_status(status)

    success = sum(1 for d in status["demos"].values() if d.get("status") == "success")
    total = len(config["demo_ppts"])
    print(f"\n{'='*60}")
    print(f"  Generation Complete: {success}/{total} successful")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    force = "--force" in sys.argv
    generate_all_demos(force=force)
