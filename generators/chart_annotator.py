"""
generators/chart_annotator.py — Matplotlib chart generation with professional styling.
Generates high-DPI PNG chart images for embedding into PPTX slides.
Now theme-aware: adapts colours and backgrounds to the active PresentationTheme.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from config import get_settings
from engine.pipeline_logger import PipelineLogger
from models import ChartData

if TYPE_CHECKING:
    from generators.themes import PresentationTheme


# ── Fallback Color Palette (used when no theme is set) ─────
COLORS = [
    "#4A90D9",  # Steel Blue
    "#2ECC71",  # Teal Green
    "#E67E22",  # Accent Orange
    "#9B59B6",  # Purple
    "#E74C3C",  # Red
    "#1ABC9C",  # Turquoise
    "#F39C12",  # Amber
    "#34495E",  # Dark Gray
]

# ── Global Style ────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 11,
    "axes.titlesize": 16,
    "axes.titleweight": "bold",
    "axes.labelsize": 12,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.2,
    "grid.linestyle": "-",
    "grid.linewidth": 0.5,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})


class ChartAnnotator:
    """Generates professional chart images from structured ChartData."""

    def __init__(self, theme: Optional[PresentationTheme] = None) -> None:
        self._settings = get_settings()
        self._log = PipelineLogger("ChartAnnotator")
        self._dpi = self._settings.chart_dpi
        self._theme = theme

    @property
    def theme(self) -> Optional[PresentationTheme]:
        return self._theme

    @theme.setter
    def theme(self, t: PresentationTheme) -> None:
        self._theme = t

    def _get_colors(self, n: Optional[int] = None) -> List[str]:
        """Return chart colour palette from theme or fallback.

        If *n* is given, return exactly *n* colours (cycling if needed).
        """
        palette = self._theme.chart_colors if self._theme else COLORS
        if n is None:
            return palette
        return [palette[i % len(palette)] for i in range(n)]

    def _get_bg_color(self) -> str:
        return self._theme.bg_white_hex if self._theme else "white"

    def _get_text_color(self) -> str:
        return self._theme.text_dark_hex if self._theme else "#2C3E50"

    def _get_muted_color(self) -> str:
        return self._theme.text_muted_hex if self._theme else "#95A5A6"

    def generate(self, chart_data: ChartData) -> io.BytesIO:
        """Generate a chart image as a PNG BytesIO buffer."""
        self._log.action("Generate Chart", f"type={chart_data.chart_type}: {chart_data.title}")

        chart_type = chart_data.chart_type.lower().replace(" ", "_")

        dispatch = {
            "bar": self._bar_chart,
            "grouped_bar": self._grouped_bar_chart,
            "stacked_bar": self._stacked_bar_chart,
            "line": self._line_chart,
            "pie": self._pie_chart,
        }

        handler = dispatch.get(chart_type, self._bar_chart)
        fig = handler(chart_data)

        # Apply theme colours to all axes
        bg = self._get_bg_color()
        text_c = self._get_text_color()
        muted_c = self._get_muted_color()
        fig.patch.set_facecolor(bg)
        for ax in fig.get_axes():
            ax.set_facecolor(bg)
            ax.tick_params(colors=text_c)
            ax.xaxis.label.set_color(text_c)
            ax.yaxis.label.set_color(text_c)
            ax.title.set_color(text_c)
            for spine in ax.spines.values():
                spine.set_color(muted_c)

        # Add source annotation
        if chart_data.source_annotation:
            fig.text(
                0.99, 0.01,
                chart_data.source_annotation,
                ha="right", va="bottom",
                fontsize=7, color=muted_c, style="italic",
                transform=fig.transFigure,
            )

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=self._dpi, bbox_inches="tight",
                    facecolor=bg, edgecolor="none")
        plt.close(fig)
        buf.seek(0)

        self._log.info(f"Chart generated: {buf.getbuffer().nbytes / 1024:.1f} KB")
        return buf

    # ── Annotations ─────────────────────────────────────────

    def _render_annotations(self, ax, data: ChartData, chart_type: str,
                            x_positions=None) -> None:
        """Render callout annotations on chart data points.

        Places annotations below the chart title area using offset points
        to avoid overlapping with title, legend, and each other.
        """
        if not data.annotations:
            return

        accent_color = self._get_colors(1)[0]
        y_lo, y_hi = ax.get_ylim()
        y_range = y_hi - y_lo
        n_labels = len(data.labels)

        for idx, ann in enumerate(data.annotations[:2]):  # Max 2 to reduce clutter
            # Validate bounds
            if ann.label_index < 0 or ann.label_index >= n_labels:
                continue
            if ann.dataset_index < 0 or ann.dataset_index >= len(data.datasets):
                continue

            y_val = data.datasets[ann.dataset_index].data[ann.label_index]

            # Determine x position based on chart type
            if chart_type == "line":
                x_val = ann.label_index
            elif x_positions is not None:
                x_val = x_positions[ann.label_index]
            else:
                x_val = ann.label_index

            # Truncate annotation text to prevent overflow
            text = ann.text if len(ann.text) <= 40 else ann.text[:37] + "..."

            # Place annotation text using offset points (pixel-based, independent
            # of data range) so they never fly above the chart axes.
            # Alternate left/right of the data point to avoid mutual overlap.
            x_offset_pts = 60 if (idx % 2 == 0) else -60
            y_offset_pts = 40 + idx * 30  # stagger vertically

            ax.annotate(
                text,
                xy=(x_val, y_val),
                xytext=(x_offset_pts, y_offset_pts),
                textcoords="offset points",
                fontsize=7,
                color=self._get_text_color(),
                ha='left' if (idx % 2 == 0) else 'right',
                va='bottom',
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor="#FFFDE7",
                    edgecolor=accent_color,
                    alpha=0.92,
                    linewidth=1.2,
                ),
                arrowprops=dict(
                    arrowstyle="->",
                    color=accent_color,
                    connectionstyle="arc3,rad=0.15",
                    linewidth=1.2,
                ),
            )

    # ── Chart Type Implementations ──────────────────────────

    def _bar_chart(self, data: ChartData) -> plt.Figure:
        fig, ax = plt.subplots(figsize=(10, 6))

        dataset = data.datasets[0] if data.datasets else None
        if dataset is None:
            ax.set_title(data.title, pad=15)
            fig.tight_layout()
            return fig
        values = dataset.data
        colors = self._get_colors()
        color = colors[0]

        bars = ax.bar(data.labels, values, color=color, width=0.6,
                      edgecolor="white", zorder=3)

        text_c = self._get_text_color()
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2, bar.get_height(),
                self._format_value(val),
                ha="center", va="bottom", fontsize=10, fontweight="bold",
                color=text_c,
            )

        ax.set_title(data.title, pad=15)
        ax.set_xlabel(data.x_axis_label)
        ax.set_ylabel(data.y_axis_label)
        ax.tick_params(axis="x", rotation=30)
        self._render_annotations(ax, data, "bar")
        fig.tight_layout()
        return fig

    def _grouped_bar_chart(self, data: ChartData) -> plt.Figure:
        import numpy as np

        fig, ax = plt.subplots(figsize=(10, 6))
        colors = self._get_colors()

        n_groups = len(data.labels)
        n_series = len(data.datasets)
        bar_width = 0.8 / n_series
        x = np.arange(n_groups)

        for i, dataset in enumerate(data.datasets):
            values = dataset.data
            # Force theme color cyclic palette, ignoring dataset.color which might be hardcoded blue from LLM
            color = colors[i % len(colors)]
            label = dataset.label or f"Series {i + 1}"
            offset = (i - n_series / 2 + 0.5) * bar_width
            ax.bar(x + offset, values, bar_width, label=label,
                   color=color, edgecolor="white")

        ax.set_title(data.title, pad=15)
        ax.set_xlabel(data.x_axis_label)
        ax.set_ylabel(data.y_axis_label)
        ax.set_xticks(x)
        ax.set_xticklabels(data.labels, rotation=30)
        ax.legend(framealpha=0.9)
        self._render_annotations(ax, data, "grouped_bar", x_positions=x)
        fig.tight_layout()
        return fig

    def _stacked_bar_chart(self, data: ChartData) -> plt.Figure:
        import numpy as np

        fig, ax = plt.subplots(figsize=(10, 6))
        colors = self._get_colors()

        x = np.arange(len(data.labels))
        bottom = np.zeros(len(data.labels))

        for i, dataset in enumerate(data.datasets):
            values = dataset.data
            color = colors[i % len(colors)]
            label = dataset.label or f"Series {i + 1}"
            ax.bar(x, values, 0.6, label=label, color=color,
                   bottom=bottom, edgecolor="white")
            bottom += np.array(values)

        ax.set_title(data.title, pad=15)
        ax.set_xlabel(data.x_axis_label)
        ax.set_ylabel(data.y_axis_label)
        ax.set_xticks(x)
        ax.set_xticklabels(data.labels, rotation=30)
        ax.legend(framealpha=0.9)
        self._render_annotations(ax, data, "stacked_bar", x_positions=x)
        fig.tight_layout()
        return fig

    def _line_chart(self, data: ChartData) -> plt.Figure:
        fig, ax = plt.subplots(figsize=(10, 6))
        colors = self._get_colors()

        for i, dataset in enumerate(data.datasets):
            values = dataset.data
            color = colors[i % len(colors)]
            label = dataset.label or f"Series {i + 1}"
            ax.plot(data.labels, values, marker="o", color=color,
                    label=label, linewidth=2, markersize=6)
            ax.fill_between(range(len(data.labels)), values, alpha=0.08, color=color)

            for j, val in enumerate(values):
                ax.annotate(
                    self._format_value(val),
                    (data.labels[j], val),
                    textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=9,
                    color=self._get_text_color(),
                )

        ax.set_title(data.title, pad=15)
        ax.set_xlabel(data.x_axis_label)
        ax.set_ylabel(data.y_axis_label)
        ax.tick_params(axis="x", rotation=30)
        if len(data.datasets) > 1:
            ax.legend(framealpha=0.9)
        self._render_annotations(ax, data, "line")
        fig.tight_layout()
        return fig

    def _pie_chart(self, data: ChartData) -> plt.Figure:
        fig, ax = plt.subplots(figsize=(8, 8))
        colors = self._get_colors()

        dataset = data.datasets[0] if data.datasets else None
        if dataset is None:
            ax.set_title(data.title, pad=20, fontsize=14, fontweight="bold")
            fig.tight_layout()
            return fig
        values = dataset.data
        pie_colors = [
            colors[i % len(colors)]
            for i, ds in enumerate(data.datasets)
        ] if len(data.datasets) == len(data.labels) else [
            colors[i % len(colors)] for i in range(len(values))
        ]

        wedges, texts, autotexts = ax.pie(
            values,
            labels=data.labels,
            colors=pie_colors,
            autopct="%1.1f%%",
            startangle=90,
            pctdistance=0.75,
        )
        text_c = self._get_text_color()
        for autotext in autotexts:
            autotext.set_fontsize(10)
            autotext.set_fontweight("bold")
        for text in texts:
            text.set_color(text_c)

        # Donut effect: white center circle
        centre_circle = plt.Circle((0, 0), 0.45, fc='white')
        ax.add_artist(centre_circle)

        ax.set_title(data.title, pad=20, fontsize=14, fontweight="bold")
        fig.tight_layout()
        return fig

    # ── Helpers ──────────────────────────────────────────────

    @staticmethod
    def _format_value(val: Any) -> str:
        """Format a numeric value for display."""
        if isinstance(val, float):
            if abs(val) >= 1_000_000:
                return f"{val / 1_000_000:.1f}M"
            if abs(val) >= 1_000:
                return f"{val / 1_000:.1f}K"
            return f"{val:.1f}"
        return str(val)
