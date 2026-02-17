"""
agents/layout_critic_agent.py — Layout validation and overlap detection.
Combines rule-based rectangle intersection with LLM-based quality assessment.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple

from agents.slide_content_agent import SlideContent
from config import Settings, get_settings
from engine.llm_provider import LLMProvider
from engine.pipeline_logger import PipelineLogger
from models import (
    BoundingBox,
    LayoutAdjustment,
    LayoutQualityAssessment,
    LayoutValidationResult,
    SlidePlan,
)
from prompts.layout_critic_prompts import LAYOUT_QUALITY_PROMPT

# Import layout constants from ppt_generator
from generators.ppt_generator import (
    HEADER_LEFT, HEADER_TOP, HEADER_WIDTH, HEADER_HEIGHT,
    CONTENT_LEFT, CONTENT_TOP, CONTENT_WIDTH, CONTENT_HEIGHT,
    SPLIT_LEFT_WIDTH,
    CHART_FULL_LEFT, CHART_FULL_TOP, CHART_FULL_WIDTH, CHART_FULL_HEIGHT,
    CHART_SPLIT_LEFT, CHART_SPLIT_TOP, CHART_SPLIT_WIDTH, CHART_SPLIT_HEIGHT,
    TABLE_LEFT, TABLE_TOP, TABLE_WIDTH, TABLE_HEIGHT,
    INSIGHT_BAR_LEFT, INSIGHT_BAR_TOP, INSIGHT_BAR_WIDTH, INSIGHT_BAR_HEIGHT,
    FOOTER_LEFT, FOOTER_TOP, FOOTER_WIDTH, FOOTER_HEIGHT,
)

# Minimum gap between elements in inches
MIN_GAP = 0.15

# Priority for adjustment (higher priority elements are never moved)
ELEMENT_PRIORITY = {
    "header": 10,
    "header_line": 9,
    "content": 5,
    "chart": 5,
    "table": 5,
    "infographic": 5,
    "insight_bar": 3,
    "footer": 2,
}


class LayoutCriticAgent:
    """Validates slide layouts for spatial overlaps and visual quality.

    Combines rule-based rectangle intersection math with LLM-based
    assessment of visual density and readability.
    """

    def __init__(
        self,
        llm: Optional[LLMProvider] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._llm = llm or LLMProvider(self._settings)
        self._log = PipelineLogger("LayoutCritic")

    def validate_slide(
        self,
        slide_number: int,
        layout_type: str,
        content: SlideContent,
        slide_plan: SlidePlan,
    ) -> LayoutValidationResult:
        """Validate a single slide's layout."""
        self._log.action("Validate Layout", f"Slide {slide_number}: {layout_type}")

        # Step 1: Build bounding boxes for all elements
        boxes = self._build_element_boxes(layout_type, content)

        # Step 2: Rule-based overlap detection
        overlaps, adjustments = self._check_overlaps(boxes)

        is_valid = len(overlaps) == 0

        # Step 3: LLM quality check
        quality_score = 0.8
        llm_feedback = ""
        density_warning = False

        try:
            quality_score, llm_feedback, density_warning = self._llm_quality_check(
                slide_number, layout_type, content, boxes
            )
        except Exception as e:
            self._log.warning(f"LLM quality check failed (non-critical): {e}")

        if overlaps:
            self._log.warning(
                f"Slide {slide_number}: {len(overlaps)} overlaps detected"
            )

        return LayoutValidationResult(
            slide_number=slide_number,
            layout_type=layout_type,
            is_valid=is_valid,
            overlaps_detected=overlaps,
            adjustments=adjustments,
            llm_quality_score=quality_score,
            llm_feedback=llm_feedback,
            density_warning=density_warning,
        )

    def validate_all(
        self,
        slides: List[SlidePlan],
        contents: List[SlideContent],
        max_workers: int = 3,
    ) -> List[LayoutValidationResult]:
        """Validate all slides concurrently."""
        self._log.action("Validate All Layouts", f"{len(slides)} slides")

        results: List[LayoutValidationResult] = []

        def _validate(args: Tuple[SlidePlan, SlideContent]) -> LayoutValidationResult:
            plan, content = args
            return self.validate_slide(
                slide_number=plan.id,
                layout_type=plan.layout_type,
                content=content,
                slide_plan=plan,
            )

        pairs = list(zip(slides, contents))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(_validate, pairs))

        invalid_count = sum(1 for r in results if not r.is_valid)
        self._log.info(
            f"Layout validation complete: {invalid_count}/{len(results)} have issues"
        )
        return results

    def _build_element_boxes(
        self, layout_type: str, content: SlideContent,
    ) -> Dict[str, BoundingBox]:
        """Build bounding boxes for all elements based on layout type."""
        boxes: Dict[str, BoundingBox] = {}

        # Header is always present (except title slides)
        if layout_type != "title":
            boxes["header"] = BoundingBox(
                left=HEADER_LEFT, top=HEADER_TOP,
                width=HEADER_WIDTH, height=HEADER_HEIGHT,
            )

        # Content area depends on layout type
        lt = layout_type.lower()

        if lt == "bullet":
            boxes["content"] = BoundingBox(
                left=CONTENT_LEFT, top=CONTENT_TOP,
                width=CONTENT_WIDTH, height=CONTENT_HEIGHT,
            )
        elif lt == "chart":
            if content.chart_data:
                boxes["chart"] = BoundingBox(
                    left=CHART_FULL_LEFT, top=CHART_FULL_TOP,
                    width=CHART_FULL_WIDTH, height=CHART_FULL_HEIGHT,
                )
            else:
                boxes["content"] = BoundingBox(
                    left=CONTENT_LEFT, top=CONTENT_TOP,
                    width=CONTENT_WIDTH, height=CONTENT_HEIGHT,
                )
        elif lt == "table":
            if content.table_data:
                boxes["table"] = BoundingBox(
                    left=TABLE_LEFT, top=TABLE_TOP,
                    width=TABLE_WIDTH, height=TABLE_HEIGHT,
                )
            else:
                boxes["content"] = BoundingBox(
                    left=CONTENT_LEFT, top=CONTENT_TOP,
                    width=CONTENT_WIDTH, height=CONTENT_HEIGHT,
                )
        elif lt == "split":
            boxes["content"] = BoundingBox(
                left=CONTENT_LEFT, top=CONTENT_TOP,
                width=SPLIT_LEFT_WIDTH, height=CONTENT_HEIGHT,
            )
            if content.chart_data:
                boxes["chart"] = BoundingBox(
                    left=CHART_SPLIT_LEFT, top=CHART_SPLIT_TOP,
                    width=CHART_SPLIT_WIDTH, height=CHART_SPLIT_HEIGHT,
                )
            elif content.table_data:
                boxes["table"] = BoundingBox(
                    left=CHART_SPLIT_LEFT, top=TABLE_TOP,
                    width=CHART_SPLIT_WIDTH, height=CHART_SPLIT_HEIGHT,
                )
            elif getattr(content, "infographic_image", None):
                boxes["infographic"] = BoundingBox(
                    left=CHART_SPLIT_LEFT, top=CHART_SPLIT_TOP,
                    width=CHART_SPLIT_WIDTH, height=CHART_SPLIT_HEIGHT,
                )

        # Infographic replaces content for bullet slides
        if lt == "bullet" and getattr(content, "infographic_image", None):
            boxes["infographic"] = boxes.pop("content", BoundingBox(
                left=CONTENT_LEFT, top=CONTENT_TOP,
                width=CONTENT_WIDTH, height=CONTENT_HEIGHT,
            ))

        # Insight bar — ppt_generator suppresses it on chart slides with data
        has_chart_data = lt == "chart" and content.chart_data is not None
        if content.key_insight and not has_chart_data:
            boxes["insight_bar"] = BoundingBox(
                left=INSIGHT_BAR_LEFT, top=INSIGHT_BAR_TOP,
                width=INSIGHT_BAR_WIDTH, height=INSIGHT_BAR_HEIGHT,
            )

        # Footer
        boxes["footer"] = BoundingBox(
            left=FOOTER_LEFT, top=FOOTER_TOP,
            width=FOOTER_WIDTH, height=FOOTER_HEIGHT,
        )

        return boxes

    def _check_overlaps(
        self, boxes: Dict[str, BoundingBox],
    ) -> Tuple[List[str], List[LayoutAdjustment]]:
        """Check all pairs for overlaps and compute adjustments."""
        overlaps: List[str] = []
        adjustments: List[LayoutAdjustment] = []

        names = list(boxes.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                name_a, name_b = names[i], names[j]
                box_a, box_b = boxes[name_a], boxes[name_b]

                if box_a.overlaps(box_b, min_gap=MIN_GAP):
                    overlap_desc = f"{name_a} overlaps {name_b}"
                    overlaps.append(overlap_desc)
                    self._log.warning(f"Overlap detected: {overlap_desc}")

                    # Adjust the lower-priority element
                    pri_a = ELEMENT_PRIORITY.get(name_a, 1)
                    pri_b = ELEMENT_PRIORITY.get(name_b, 1)

                    if pri_a >= pri_b:
                        to_move, anchor = name_b, name_a
                        move_box, anchor_box = box_b, box_a
                    else:
                        to_move, anchor = name_a, name_b
                        move_box, anchor_box = box_a, box_b

                    adjusted = self._auto_fix_overlap(move_box, anchor_box)
                    adjustments.append(LayoutAdjustment(
                        element_name=to_move,
                        original=move_box,
                        adjusted=adjusted,
                        reason=f"Moved to avoid overlap with {anchor}",
                    ))

        return overlaps, adjustments

    @staticmethod
    def _auto_fix_overlap(
        move_box: BoundingBox, anchor_box: BoundingBox,
    ) -> BoundingBox:
        """Compute an adjusted bounding box to resolve an overlap.

        Strategy: If the element-to-move is below the anchor, push it down.
        If above, reduce its height. Always maintain MIN_GAP.
        """
        if move_box.top >= anchor_box.top:
            # Element is below anchor — shift it down below anchor's bottom
            new_top = anchor_box.bottom + MIN_GAP
            available_height = 7.5 - new_top - 0.1  # leave 0.1" margin at slide bottom
            new_height = min(move_box.height, max(available_height, 0.2))
            return BoundingBox(
                left=move_box.left, top=new_top,
                width=move_box.width, height=new_height,
            )
        else:
            # Element is above anchor — shrink its height
            max_bottom = anchor_box.top - MIN_GAP
            new_height = max(max_bottom - move_box.top, 0.2)
            return BoundingBox(
                left=move_box.left, top=move_box.top,
                width=move_box.width, height=new_height,
            )

    def _llm_quality_check(
        self,
        slide_number: int,
        layout_type: str,
        content: SlideContent,
        boxes: Dict[str, BoundingBox],
    ) -> Tuple[float, str, bool]:
        """Use Gemini to evaluate visual density and readability."""
        # Build positions description
        pos_lines = []
        for name, box in boxes.items():
            pos_lines.append(
                f"  {name}: left={box.left:.1f}, top={box.top:.1f}, "
                f"width={box.width:.1f}, height={box.height:.1f} "
                f"(bottom={box.bottom:.1f})"
            )

        prompt = LAYOUT_QUALITY_PROMPT.format(
            slide_number=slide_number,
            slide_title=content.title,
            layout_type=layout_type,
            num_bullets=len(content.content_bullets),
            has_chart=content.chart_data is not None,
            has_table=content.table_data is not None,
            has_infographic=getattr(content, "infographic_image", None) is not None,
            has_insight=bool(content.key_insight),
            element_positions="\n".join(pos_lines),
        )

        result = self._llm.generate_structured(
            prompt=prompt,
            response_model=LayoutQualityAssessment,
            model=self._settings.gemini_flash_model,
            temperature=0.2,
        )

        return result.quality_score, result.feedback, result.density_warning
