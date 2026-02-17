"""
generators/themes.py — Centralised presentation theme definitions.
Each theme provides colours for both python-pptx (RGBColor) and
matplotlib (normalised 0-1 tuples) so the PPTX generator and the
slide previewer stay perfectly in sync.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from pptx.dml.color import RGBColor


def _hex(h: str) -> RGBColor:
    """Convert '#RRGGBB' to pptx RGBColor."""
    h = h.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _norm(h: str) -> Tuple[float, float, float]:
    """Convert '#RRGGBB' to matplotlib normalised (0-1) tuple."""
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)


@dataclass
class PresentationTheme:
    """A complete colour / font palette for one visual style."""

    # Metadata
    name: str
    display_name: str
    description: str

    # Core colours (hex strings — derived properties produce RGBColor / mpl tuples)
    primary_hex: str       # Title slide bg, header accents
    accent_hex: str        # Accent lines, highlights  
    text_dark_hex: str     # Body text on light bg
    text_muted_hex: str    # Footnotes, slide numbers
    bg_light_hex: str      # Alternating row / card bg
    bg_white_hex: str = "#FFFFFF"
    insight_bg_hex: str = "#EBF5FB"  # Bottom insight bar background

    # Chart colour palette (hex list)
    chart_colors: List[str] = field(default_factory=lambda: [
        "#4A90D9", "#2ECC71", "#E67E22", "#9B59B6",
        "#E74C3C", "#1ABC9C", "#F39C12", "#34495E",
    ])

    # Fonts
    font_family: str = "Segoe UI"
    heading_font: str = "Segoe UI"
    body_font: str = "Segoe UI"

    # Gradient & visual flags
    gradient_end_hex: str = ""   # Secondary gradient colour (auto-derived if empty)
    is_dark: bool = False        # Whether this is a dark-background theme

    # ── Derived: python-pptx RGBColor ──────────────────────
    @property
    def primary(self) -> RGBColor:
        return _hex(self.primary_hex)

    @property
    def accent(self) -> RGBColor:
        return _hex(self.accent_hex)

    @property
    def text_dark(self) -> RGBColor:
        return _hex(self.text_dark_hex)

    @property
    def text_muted(self) -> RGBColor:
        return _hex(self.text_muted_hex)

    @property
    def bg_light(self) -> RGBColor:
        return _hex(self.bg_light_hex)

    @property
    def bg_white(self) -> RGBColor:
        return _hex(self.bg_white_hex)

    @property
    def insight_bg(self) -> RGBColor:
        return _hex(self.insight_bg_hex)

    # ── Derived: matplotlib normalised tuples ──────────────
    @property
    def mpl_primary(self) -> Tuple[float, float, float]:
        return _norm(self.primary_hex)

    @property
    def mpl_accent(self) -> Tuple[float, float, float]:
        return _norm(self.accent_hex)

    @property
    def mpl_text_dark(self) -> Tuple[float, float, float]:
        return _norm(self.text_dark_hex)

    @property
    def mpl_text_muted(self) -> Tuple[float, float, float]:
        return _norm(self.text_muted_hex)

    @property
    def mpl_bg_light(self) -> Tuple[float, float, float]:
        return _norm(self.bg_light_hex)

    @property
    def mpl_bg_white(self) -> Tuple[float, float, float]:
        return _norm(self.bg_white_hex)

    @property
    def mpl_insight_bg(self) -> Tuple[float, float, float]:
        return _norm(self.insight_bg_hex)

    # ── Derived: gradient colours ────────────────────────────
    @property
    def is_dark_background(self) -> bool:
        """Auto-detect if bg_white is dark (luminance < 0.5)."""
        r, g, b = _norm(self.bg_white_hex)
        return (0.299 * r + 0.587 * g + 0.114 * b) < 0.5

    @property
    def gradient_end(self) -> RGBColor:
        """Secondary gradient colour, auto-derived if not set."""
        if self.gradient_end_hex:
            return _hex(self.gradient_end_hex)
        h = self.primary_hex.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        f = 0.4
        return RGBColor(min(255, int(r + (255 - r) * f)),
                        min(255, int(g + (255 - g) * f)),
                        min(255, int(b + (255 - b) * f)))

    @property
    def mpl_gradient_end(self) -> Tuple[float, float, float]:
        if self.gradient_end_hex:
            return _norm(self.gradient_end_hex)
        r, g, b = _norm(self.primary_hex)
        f = 0.4
        return (r + (1.0 - r) * f, g + (1.0 - g) * f, b + (1.0 - b) * f)

    def to_dict(self) -> Dict:
        """Serialise for session-state storage."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "primary_hex": self.primary_hex,
            "accent_hex": self.accent_hex,
            "text_dark_hex": self.text_dark_hex,
            "text_muted_hex": self.text_muted_hex,
            "bg_light_hex": self.bg_light_hex,
            "bg_white_hex": self.bg_white_hex,
            "insight_bg_hex": self.insight_bg_hex,
            "chart_colors": self.chart_colors,
            "font_family": self.font_family,
            "heading_font": self.heading_font,
            "body_font": self.body_font,
            "gradient_end_hex": self.gradient_end_hex,
            "is_dark": self.is_dark,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> PresentationTheme:
        return cls(**d)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Built-in Themes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

THEME_CORPORATE_BLUE = PresentationTheme(
    name="corporate_blue",
    display_name="Corporate Blue",
    description="Classic navy & steel-blue — trusted, authoritative, boardroom-ready",
    primary_hex="#1B2A4A",
    accent_hex="#4A90D9",
    text_dark_hex="#2C3E50",
    text_muted_hex="#95A5A6",
    bg_light_hex="#F8F9FA",
    insight_bg_hex="#EBF5FB",
    chart_colors=["#4A90D9", "#2ECC71", "#E67E22", "#9B59B6",
                  "#E74C3C", "#1ABC9C", "#F39C12", "#34495E"],
    font_family="Segoe UI",
    heading_font="Segoe UI",
    body_font="Segoe UI",
    gradient_end_hex="#2C4A7C",
    is_dark=False,
)

THEME_MODERN_EMERALD = PresentationTheme(
    name="modern_emerald",
    display_name="Modern Emerald",
    description="Dark charcoal with emerald accents — sleek, modern, high-contrast",
    primary_hex="#1A1A2E",
    accent_hex="#16A085",
    text_dark_hex="#ECF0F1",
    text_muted_hex="#7F8C8D",
    bg_light_hex="#222240",
    bg_white_hex="#16162B",
    insight_bg_hex="#0D3D36",
    chart_colors=["#16A085", "#E74C3C", "#F39C12", "#3498DB",
                  "#9B59B6", "#2ECC71", "#E67E22", "#1ABC9C"],
    font_family="Segoe UI",
    heading_font="Segoe UI",
    body_font="Segoe UI",
    gradient_end_hex="#2A2A4E",
    is_dark=True,
)

THEME_WARM_EXECUTIVE = PresentationTheme(
    name="warm_executive",
    display_name="Warm Executive",
    description="Rich burgundy with gold accents — elegant, premium, C-suite polish",
    primary_hex="#3B1929",
    accent_hex="#C9963B",
    text_dark_hex="#2C2C2C",
    text_muted_hex="#8E7A6D",
    bg_light_hex="#FAF5EF",
    bg_white_hex="#FFFDF9",
    insight_bg_hex="#F5ECD7",
    chart_colors=["#C9963B", "#6B3A3A", "#4A7C59", "#3C6EA5",
                  "#8E5B4D", "#D4A76A", "#5C8374", "#9B7DB8"],
    font_family="Georgia",
    heading_font="Georgia",
    body_font="Georgia",
    gradient_end_hex="#5C2A3E",
    is_dark=False,
)

THEME_MIDNIGHT_VIOLET = PresentationTheme(
    name="midnight_violet",
    display_name="Midnight Violet",
    description="Deep purple with electric violet highlights — bold, creative, future-forward",
    primary_hex="#1A0A2E",
    accent_hex="#7C3AED",
    text_dark_hex="#E8E0F0",
    text_muted_hex="#8B7FA8",
    bg_light_hex="#251545",
    bg_white_hex="#140A28",
    insight_bg_hex="#2D1B69",
    chart_colors=["#7C3AED", "#EC4899", "#06B6D4", "#F59E0B",
                  "#10B981", "#F43F5E", "#8B5CF6", "#14B8A6"],
    font_family="Segoe UI",
    heading_font="Segoe UI",
    body_font="Segoe UI",
    gradient_end_hex="#2E1A50",
    is_dark=True,
)

THEME_NIPPON_RED = PresentationTheme(
    name="nippon_red",
    display_name="Nippon Red",
    description="Japanese-inspired crimson & ivory — bold, striking, unmistakable presence",
    primary_hex="#8B0000",
    accent_hex="#D63031",
    text_dark_hex="#1A1A1A",
    text_muted_hex="#8C8C8C",
    bg_light_hex="#FDF5F0",
    bg_white_hex="#FFFAF5",
    insight_bg_hex="#FDECEA",
    chart_colors=["#D63031", "#2D3436", "#6C5B7B", "#F7DC6F",
                  "#1ABC9C", "#E17055", "#0984E3", "#636E72"],
    font_family="Segoe UI",
    heading_font="Segoe UI",
    body_font="Segoe UI",
    gradient_end_hex="#B22222",
    is_dark=False,
)

# Registry
BUILTIN_THEMES: Dict[str, PresentationTheme] = {
    t.name: t for t in [
        THEME_CORPORATE_BLUE,
        THEME_MODERN_EMERALD,
        THEME_WARM_EXECUTIVE,
        THEME_MIDNIGHT_VIOLET,
        THEME_NIPPON_RED,
    ]
}


def get_theme(name: str) -> PresentationTheme:
    """Return a theme by its short name (e.g. 'corporate_blue')."""
    if name not in BUILTIN_THEMES:
        raise ValueError(
            f"Unknown theme '{name}'. Available: {list(BUILTIN_THEMES.keys())}"
        )
    return BUILTIN_THEMES[name]


def pick_two_themes(exclude: str | None = None) -> Tuple[PresentationTheme, PresentationTheme]:
    """Pick two contrasting themes for the user to choose between.

    Always returns corporate_blue plus a dark-mode option.
    """
    import random
    dark_themes = [t for t in BUILTIN_THEMES.values() if t.name != "corporate_blue"]
    if exclude and exclude != "corporate_blue":
        dark_themes = [t for t in dark_themes if t.name != exclude]
    second = random.choice(dark_themes) if dark_themes else THEME_MODERN_EMERALD
    return THEME_CORPORATE_BLUE, second
