"""CLI entry point for the Cyberknight PDF renderer.

Usage:
    cyberknight-pdf-render path/to/report.md
    cyberknight-pdf-render archive/2026-q1-membership/
    cyberknight-pdf-render --theme moon path/to/report.md   # single theme only

By default, renders all three themes (moon, dawn, mono) producing
three PDFs with theme suffixes (e.g. report-moon.pdf, report-dawn.pdf,
report-mono.pdf). Pass --theme to render a single theme.
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

# macOS: WeasyPrint needs Homebrew's Pango/Cairo/GLib dynamic libraries.
# Inject the Homebrew lib path before any imports so ctypes can find them.
def _ensure_homebrew_libs() -> None:
    homebrew_lib = "/opt/homebrew/lib"
    if sys.platform == "darwin" and os.path.isdir(homebrew_lib):
        existing = os.environ.get("DYLD_LIBRARY_PATH", "")
        if homebrew_lib not in existing:
            os.environ["DYLD_LIBRARY_PATH"] = (
                f"{homebrew_lib}:{existing}" if existing else homebrew_lib
            )

_ensure_homebrew_libs()

import jinja2
from weasyprint import HTML

from renderer.md_to_html import convert
from renderer.themes import THEMES, emit_css_variables


def _find_fonts_dir() -> Path:
    """Resolve the fonts directory relative to this module."""
    return Path(__file__).parent / "fonts"


def _find_element_pages(document):
    """Return dict mapping element_id -> set of page indices."""
    mapping: dict[str, set[int]] = {}
    for page_index, page in enumerate(document.pages):
        def traverse(box):
            element = getattr(box, "element", None)
            if element is not None:
                element_id = element.get("id")
                if element_id:
                    mapping.setdefault(element_id, set()).add(page_index)
            for child in getattr(box, "children", []):
                traverse(child)
        traverse(page._page_box)
    return mapping


def _validate_sections(document, sections):
    """Check each H2 section fits on a single page. Return overflowing titles."""
    page_of = _find_element_pages(document)
    overflowing: list[str] = []
    present_indices: list[int] = []
    for i, section in enumerate(sections):
        sid = section.id
        start_pages = page_of.get(sid, set())
        end_pages = page_of.get(f"end-{sid}", set())
        if not start_pages:
            continue
        present_indices.append(i)
        if not end_pages:
            overflowing.append(section.title)
        elif len(start_pages) > 1 or len(end_pages) > 1:
            overflowing.append(section.title)
        elif start_pages != end_pages:
            overflowing.append(section.title)
    if present_indices and present_indices[-1] < len(sections) - 1:
        culprit = sections[present_indices[-1]].title
        if culprit not in overflowing:
            overflowing.append(culprit)
    return overflowing


def main() -> None:
    # ── Parse arguments ──
    args = sys.argv[1:]
    themes_to_render: list[str] = []  # empty means "all"

    if args and args[0] == "--theme":
        if len(args) < 2:
            print("Error: --theme requires a value (moon, dawn, or mono)", file=sys.stderr)
            sys.exit(1)
        theme = args[1]
        if theme not in THEMES:
            print(
                f"Error: unknown theme '{theme}'. Choose from: {', '.join(THEMES)}",
                file=sys.stderr,
            )
            sys.exit(1)
        themes_to_render = [theme]
        args = args[2:]

    if not args:
        print(
            "Usage: cyberknight-pdf-render [--theme moon|dawn|mono]"
            " <path/to/report.md | path/to/report-folder/>",
            file=sys.stderr,
        )
        sys.exit(1)

    input_path = Path(args[0])

    # Resolve the .md file and output directory
    if input_path.is_dir():
        md_candidates = sorted(input_path.glob("*.md"))
        if not md_candidates:
            print(f"Error: no .md file found in {input_path}", file=sys.stderr)
            sys.exit(1)
        md_path = md_candidates[0]
        output_dir = input_path
    elif input_path.suffix == ".md":
        md_path = input_path
        output_dir = md_path.parent
    else:
        print(
            f"Error: {input_path} is not a directory or .md file",
            file=sys.stderr,
        )
        sys.exit(1)

    if not md_path.exists():
        print(f"Error: {md_path} not found", file=sys.stderr)
        sys.exit(1)

    # ── Parse markdown → ReportData (once) ──
    print(f"📄 Parsing: {md_path}")
    data = convert(md_path)

    # ── Load Jinja2 template (once) ──
    template_dir = Path(__file__).parent
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(template_dir)),
        autoescape=False,  # we emit raw HTML from mistune
    )
    template = env.get_template("template.html")
    fonts_dir = _find_fonts_dir()

    # ── Render each theme ──
    if not themes_to_render:
        themes_to_render = list(THEMES.keys())

    for theme_name in themes_to_render:
        output_path = output_dir / f"{md_path.stem}-{theme_name}.pdf"

        html = template.render(
            title=data.title,
            subtitle=data.subtitle,
            date=f"Rendered on {date.today():%B %d, %Y}",
            toc=data.toc,
            sections=data.sections,
            fonts_dir=str(fonts_dir),
            css_variables=emit_css_variables(theme_name),
        )

        print(f"📦 Building PDF ({theme_name}): {output_path}")
        doc = HTML(string=html).render()
        overflowing = _validate_sections(doc, data.sections)
        if overflowing:
            print(
                "Error: The following section(s) exceed one page:", file=sys.stderr
            )
            for title in overflowing:
                print(f"  - {title}", file=sys.stderr)
            sys.exit(1)
        doc.write_pdf(target=str(output_path))

    print(f"✅ Done — {len(themes_to_render)} PDF(s) generated in {output_dir}")


if __name__ == "__main__":
    main()
