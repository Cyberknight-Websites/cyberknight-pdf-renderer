"""Markdown → HTML converter with Rosé Pine Dawn structure.

Produces a title, TOC entries, and section HTML for the Jinja2 template.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import mistune


# ── Data structures ──────────────────────────────────────────────────────

@dataclass
class TocEntry:
    label: str
    level: str  # "h2" or "h3"
    id: str


@dataclass
class Section:
    title: str
    id: str
    body_html: str


@dataclass
class ReportData:
    title: str
    subtitle: str
    toc: list[TocEntry]
    sections: list[Section]


# ── Slug helper ─────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    """Generate a URL-safe slug from heading text."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


# ── CSV table directive ─────────────────────────────────────────────────

_DIRECTIVE_TABLE = "!table("


def _process_table_directive(line: str) -> str:
    """Process a !table(path/to/file.csv) directive, return HTML table."""
    raw = line.strip()
    inner = raw[len(_DIRECTIVE_TABLE):]
    if inner.endswith(")"):
        inner = inner[:-1]
    csv_path = inner.strip()

    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
    except Exception:
        return '<p class="error">[Table not found or unreadable: {}]</p>'.format(
            csv_path
        )

    if not rows:
        return ""

    html = '<table><thead><tr>'
    headers = rows[0]
    for h in headers:
        html += f"<th>{_escape_html(h)}</th>"
    html += "</tr></thead><tbody>"

    for row in rows[1:]:
        html += "<tr>"
        # Pad short rows
        padded = row + [""] * (len(headers) - len(row))
        for cell in padded[:len(headers)]:
            html += f"<td>{_escape_html(cell)}</td>"
        html += "</tr>"

    html += "</tbody></table>"
    return html


def _escape_html(text: str) -> str:
    """Escape HTML entities in plain text."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ── AST-to-HTML renderer ─────────────────────────────────────────────────

class _SectionHTMLRenderer:
    """Renders AST tokens for a single section into HTML."""

    def __init__(self, md_dir: Path):
        self.md_dir = md_dir

    def render(self, tokens: list[dict[str, Any]]) -> str:
        parts = []
        for token in tokens:
            parts.append(self._render_token(token))
        return "\n".join(p for p in parts if p)

    def _render_token(self, token: dict[str, Any]) -> str:
        t = token["type"]
        children = token.get("children", [])

        if t == "heading":
            level = token["attrs"]["level"]
            text = self._extract_text(token)
            sid = _slugify(text)
            return f'<h{level} id="{sid}">{text}</h{level}>'

        elif t == "paragraph":
            raw = self._extract_text(token)
            if raw.strip().startswith(_DIRECTIVE_TABLE):
                return _process_table_directive(raw)
            text = self._render_inlines(children)
            if text.strip():
                return f"<p>{text}</p>"
            return ""

        elif t == "block_code":
            code = token.get("raw", "")
            if code and code.endswith("\n"):
                code = code[:-1]
            escaped = _escape_html(code)
            return f"<pre><code>{escaped}</code></pre>"

        elif t == "list":
            ordered = token.get("attrs", {}).get("ordered", False)
            tag = "ol" if ordered else "ul"
            items = self._render_list_items(children)
            return f"<{tag}>{items}</{tag}>"

        elif t == "block_quote":
            text = self._render_inlines(children)
            return f"<blockquote>{text}</blockquote>"

        elif t == "thematic_break":
            return "<hr>"

        elif t == "table":
            return self._render_table(children)

        elif t == "blank_line":
            return ""

        # Recurse into children for other types
        if children:
            sub = []
            for child in children:
                sub.append(self._render_token(child))
            return "\n".join(s for s in sub if s)

        return ""

    def _render_table(self, children: list[dict[str, Any]]) -> str:
        html = "<table>"
        for child in children:
            if child["type"] == "table_head":
                html += "<thead><tr>"
                for cell in child.get("children", []):
                    text = self._extract_text(cell)
                    html += f"<th>{text}</th>"
                html += "</tr></thead>"
            elif child["type"] == "table_body":
                html += "<tbody>"
                for row in child.get("children", []):
                    html += "<tr>"
                    for cell in row.get("children", []):
                        text = self._extract_text(cell)
                        html += f"<td>{text}</td>"
                    html += "</tr>"
                html += "</tbody>"
        html += "</table>"
        return html

    def _render_list_items(self, children: list[dict[str, Any]]) -> str:
        items = []
        for child in children:
            if child["type"] == "list_item":
                # Extract content from list item children
                content_parts = []
                for item_child in child.get("children", []):
                    if item_child["type"] in ("paragraph", "block_text"):
                        text = self._render_inlines(
                            item_child.get("children", [])
                        )
                        content_parts.append(text)
                    elif item_child["type"] == "list":
                        sub = self._render_list_items(
                            item_child.get("children", [])
                        )
                        content_parts.append(sub)
                    elif item_child["type"] == "block_code":
                        code = item_child.get("raw", "")
                        if code and code.endswith("\n"):
                            code = code[:-1]
                        content_parts.append(
                            f"<pre><code>{_escape_html(code)}</code></pre>"
                        )
                    elif item_child["type"] == "block_quote":
                        text = self._render_inlines(
                            item_child.get("children", [])
                        )
                        content_parts.append(f"<blockquote>{text}</blockquote>")
                items.append(f"<li>{' '.join(content_parts)}</li>")
        return "\n".join(items)

    def _render_inlines(self, children: list[dict[str, Any]]) -> str:
        """Render inline elements (text, bold, italic, code, links, images)."""
        parts = []
        for child in children:
            t = child["type"]
            if t == "text":
                parts.append(_escape_html(child.get("raw", "")))
            elif t == "strong":
                inner = self._render_inlines(child.get("children", []))
                parts.append(f"<strong>{inner}</strong>")
            elif t == "emphasis":
                inner = self._render_inlines(child.get("children", []))
                parts.append(f"<em>{inner}</em>")
            elif t == "codespan":
                code = _escape_html(child.get("raw", ""))
                parts.append(f"<code>{code}</code>")
            elif t == "link":
                href = _escape_html(child.get("attrs", {}).get("url", ""))
                inner = self._render_inlines(child.get("children", []))
                parts.append(f'<a href="{href}">{inner}</a>')
            elif t == "image":
                src = child.get("attrs", {}).get("url", "")
                alt = _escape_html(child.get("attrs", {}).get("alt", ""))
                if not src.startswith(("http://", "https://", "/")):
                    src = str(self.md_dir / src)
                parts.append(f'<img src="{src}" alt="{alt}">')
            elif t == "softbreak":
                parts.append(" ")
            elif t == "linebreak":
                parts.append("<br>")
            elif t == "html":
                parts.append(child.get("raw", ""))
            elif "children" in child:
                parts.append(self._render_inlines(child["children"]))
        return "".join(parts)

    def _extract_text(self, token: dict[str, Any]) -> str:
        """Extract plain text from any AST token."""
        if "raw" in token and isinstance(token.get("raw"), str):
            return token["raw"]
        parts = []
        if "children" in token:
            for child in token["children"]:
                if child["type"] == "text":
                    parts.append(child.get("raw", ""))
                elif child["type"] == "softbreak":
                    parts.append(" ")
                elif child["type"] == "linebreak":
                    parts.append(" ")
                elif child["type"] == "codespan":
                    parts.append(child.get("raw", ""))
                elif child["type"] == "strong":
                    parts.append(self._extract_text(child))
                elif child["type"] == "emphasis":
                    parts.append(self._extract_text(child))
                elif child["type"] == "link":
                    parts.append(self._extract_text(child))
                elif child["type"] == "image":
                    parts.append(child.get("attrs", {}).get("alt", ""))
                elif "children" in child:
                    parts.append(self._extract_text(child))
                elif "raw" in child:
                    parts.append(str(child["raw"]))
        return "".join(parts)


# ── Content wrapper ─────────────────────────────────────────────────────

def _is_image_only_group(lines: list[str]) -> bool:
    """Check if a group consists primarily of an image with optional caption.

    Such groups are rendered bare (no .surface wrapper) to avoid large
    empty bordered boxes when an image is the only content.
    """
    joined = "\n".join(lines).strip()
    if not joined or "<img" not in joined:
        return False

    # Must not contain headings, code blocks, tables, lists, or blockquotes
    if re.search(r'<(h3|pre|table|ul|ol|blockquote)\b', joined):
        return False

    # Strip tags and measure remaining text; more than ~400 chars of
    # prose means it should stay in a surface box.
    text_only = re.sub(r'<[^>]+>', '', joined).strip()
    return len(text_only) <= 400


def _wrap_surface_content(html: str) -> str:
    """Wrap content into .surface divs; H3 headings start a new surface.
    Image-only groups (with optional caption) are rendered bare."""
    # Protect multi-line block elements (pre, table, ul, ol, blockquote)
    # from being fragmented by the line-based grouping logic below.
    protected: dict[str, str] = {}

    def _protect(m: re.Match) -> str:
        key = f"<PROTECTED-{len(protected)}>"
        protected[key] = m.group(0)
        return key

    html = re.sub(r'<(pre|table|ul|ol|blockquote)\b.*?</\1>', _protect, html, flags=re.DOTALL)

    def flush_group(group: list[str]) -> None:
        if not group:
            return
        if _is_image_only_group(group):
            result.append("\n".join(group))
        else:
            result.append(
                '<div class="surface">\n' + "\n".join(group) + "\n</div>"
            )

    lines = html.strip().split("\n")
    result: list[str] = []
    current_group: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("<h3"):
            flush_group(current_group)
            current_group = []
            current_group.append(stripped)
        else:
            current_group.append(stripped)

    flush_group(current_group)

    result_str = "\n".join(result)
    for placeholder, original in protected.items():
        result_str = result_str.replace(placeholder, original)
    return result_str


# ── Public API ───────────────────────────────────────────────────────────

def convert(md_path: Path) -> ReportData:
    """Convert a markdown file into a ReportData for the template.

    Args:
        md_path: Path to the .md source file.

    Returns:
        ReportData with title, subtitle, TOC entries, and sections.
    """
    text = md_path.read_text(encoding="utf-8")

    # Strip YAML frontmatter
    text = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, count=1, flags=re.DOTALL)

    markdown = mistune.create_markdown(renderer="ast", plugins=["table"])
    ast: list[dict[str, Any]] = markdown(text)  # type: ignore[assignment]

    renderer = _SectionHTMLRenderer(md_path.parent)

    title = ""
    subtitle = ""
    toc: list[TocEntry] = []
    sections: list[Section] = []

    # Current section accumulator
    current_heading: dict | None = None
    current_tokens: list[dict] = []

    def flush_section():
        nonlocal current_heading, current_tokens
        if current_heading:
            h_text = current_heading["text"]
            h_level = current_heading["level"]
            h_id = _slugify(h_text)

            body_html = renderer.render(current_tokens)
            wrapped = _wrap_surface_content(body_html)
            sections.append(Section(title=h_text, id=h_id, body_html=wrapped))
            toc.append(TocEntry(label=h_text, level=f"h{h_level}", id=h_id))

        current_heading = None
        current_tokens = []

    for token in ast:
        t = token["type"]

        if t == "heading":
            level = token["attrs"]["level"]
            text = _extract_text(token)

            if level == 1:
                if not title:
                    title = text
                elif not subtitle:
                    subtitle = text
                continue

            # H2 or H3 → flush previous, start new section
            if level == 2:
                flush_section()
                current_heading = {"text": text, "level": level}
            elif level == 3:
                # H3 is kept within the current section
                current_tokens.append(token)

        elif t in ("blank_line",):
            pass  # skip blank lines in token stream
        else:
            current_tokens.append(token)

    # Flush final section
    flush_section()

    return ReportData(
        title=title,
        subtitle=subtitle,
        toc=toc,
        sections=sections,
    )


def _extract_text(token: dict[str, Any]) -> str:
    """Extract plain text from any AST token (module-level helper)."""
    if "raw" in token and isinstance(token.get("raw"), str):
        return token["raw"]
    parts = []
    if "children" in token:
        for child in token["children"]:
            if child["type"] == "text":
                parts.append(child.get("raw", ""))
            elif child["type"] == "softbreak":
                parts.append(" ")
            elif child["type"] == "linebreak":
                parts.append(" ")
            elif child["type"] == "codespan":
                parts.append(child.get("raw", ""))
            elif child["type"] == "strong":
                parts.append(_extract_text(child))
            elif child["type"] == "emphasis":
                parts.append(_extract_text(child))
            elif child["type"] == "link":
                parts.append(_extract_text(child))
            elif child["type"] == "image":
                parts.append(child.get("attrs", {}).get("alt", ""))
            elif "children" in child:
                parts.append(_extract_text(child))
            elif "raw" in child:
                parts.append(str(child["raw"]))
    return "".join(parts)
