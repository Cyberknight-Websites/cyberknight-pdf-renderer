"""Theme palettes for the report renderer.

Each theme is a dict mapping CSS custom property names to hex colour values.
The emit_css_variables() function turns a theme dict into the :root { ... }
CSS block that the Jinja2 template injects into the stylesheet.
"""

from __future__ import annotations

# ── Rosé Pine Moon (dark) ────────────────────────────────────────────────

MOON: dict[str, str] = {
    "base":     "#232136",
    "surface":  "#2a273f",
    "overlay":  "#393552",
    "muted":    "#6e6a86",
    "subtle":   "#908caa",
    "text":     "#e0def4",
    "love":     "#eb6f92",
    "gold":     "#f6c177",
    "rose":     "#ea9a97",
    "pine":     "#3e8fb0",
    "foam":     "#9ccfd8",
    "iris":     "#c4a7e7",
    "hl_low":   "#2a283e",
    "hl_med":   "#44415a",
    "hl_high":  "#56526e",
    "header_bg":   "#c4a7e7",
    "header_text": "#ffffff",
}

# ── Rosé Pine Dawn (light) ──────────────────────────────────────────────

DAWN: dict[str, str] = {
    "base":     "#faf4ed",
    "surface":  "#fffaf3",
    "overlay":  "#f2e9e1",
    "muted":    "#9893a5",
    "subtle":   "#797593",
    "text":     "#575279",
    "love":     "#b4637a",
    "gold":     "#ea9d34",
    "rose":     "#d7827e",
    "pine":     "#286983",
    "foam":     "#56949f",
    "iris":     "#907aa9",
    "hl_low":   "#f4ede8",
    "hl_med":   "#dfdad9",
    "hl_high":  "#cecacd",
    "header_bg":   "#907aa9",
    "header_text": "#ffffff",
}

# ── Monochrome (print-friendly) ─────────────────────────────────────────

MONO: dict[str, str] = {
    "base":     "#ffffff",
    "surface":  "#ffffff",
    "overlay":  "#eaeaea",
    "muted":    "#808080",
    "subtle":   "#a0a0a0",
    "text":     "#000000",
    "love":     "#000000",
    "gold":     "#000000",
    "rose":     "#000000",
    "pine":     "#000000",
    "foam":     "#000000",
    "iris":     "#777777",
    "hl_low":   "#f2f2f2",
    "hl_med":   "#d6d6d6",
    "hl_high":  "#b0b0b0",
    "header_bg":   "#ffffff",
    "header_text": "#000000",
}

# ── Public API ───────────────────────────────────────────────────────────

THEMES: dict[str, dict[str, str]] = {
    "moon": MOON,
    "dawn": DAWN,
    "mono": MONO,
}


def emit_css_variables(theme_name: str) -> str:
    """Return a CSS :root block with the given theme's colour variables.

    Args:
        theme_name: One of "moon", "dawn", or "mono".

    Returns:
        A string like ``:root { --base: #232136; ... }`` ready to inject
        into the stylesheet.
    """
    palette = THEMES[theme_name]
    lines = [":root {"]
    for var, hex_val in palette.items():
        lines.append(f"    --{var}: {hex_val};")
    lines.append("}")
    return "\n".join(lines)
