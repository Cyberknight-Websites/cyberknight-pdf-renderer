# cyberknight-pdf-renderer

Rosé Pine themed PDF report generator from Markdown. Produces print-ready,
letter-size PDFs with JetBrains Mono typography. Supports dark, light,
and printable (greyscale) colour themes.

## Prerequisites

- **Python 3.12+**
- **Pango, Cairo, GLib** — WeasyPrint's system dependencies

### macOS

```bash
brew install pango
```

### Linux (Debian/Ubuntu)

```bash
sudo apt install libpango-1.0-0 libpangocairo-1.0-0 libcairo2
```

## Installation

```bash
git clone git@github.com:Cyberknight-Websites/cyberknight-pdf-renderer.git
cd cyberknight-pdf-renderer
uv tool install --editable .
```

This makes `cyberknight-pdf-render` globally available on your system.

To upgrade after pulling changes:

```bash
uv tool install --editable . --force
```

## Usage

```bash
# Render a Markdown file with all three themes (dark, light, printable)
cyberknight-pdf-render path/to/report.md

# Render with a single theme
cyberknight-pdf-render --theme light path/to/report.md

# Point at a directory containing a single .md file
cyberknight-pdf-render archive/2026-q1-membership/
```

PDFs are written alongside the source `.md` file with theme suffixes:
`report-dark.pdf`, `report-light.pdf`, `report-printable.pdf`.

## Markdown features

- Standard Markdown (headings, lists, tables, code blocks, blockquotes, images)
- `!table(path/to/data.csv)` directive for inline CSV tables
- H1 headings become the title page; H2 headings start new pages
- H3 headings create surface boxes within a section
- Section overflow validation — if any H2 section exceeds one page, the
  renderer exits with an error and lists the offending sections

## Themes

| Theme | Use case |
|-------|----------|
| `dark` | Dark mode, presentations |
| `light` | Light mode, screen reading |
| `printable` | Print-friendly, greyscale |

## Development

```bash
uv sync
uv run cyberknight-pdf-render path/to/report.md
```

## License

MIT — see [LICENSE](LICENSE).
