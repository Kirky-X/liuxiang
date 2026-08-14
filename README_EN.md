# Liuxiang — Academic Research Suite

[中文](README.md) | English

[![GitHub Release](https://img.shields.io/github/v/release/Kirky-X/liuxiang?style=flat-square)](https://github.com/Kirky-X/liuxiang/releases) [![GitHub License](https://img.shields.io/github/license/Kirky-X/liuxiang?style=flat-square)](LICENSE)

Liuxiang is an AI agent skill for the full academic research lifecycle — from literature search to paper finalization. Four independent yet composable modules cover multi-source paper discovery, lossless LaTeX/PDF conversion, multi-agent paper writing, and peer review.

## Features

### Four Modules

| Module | Description | Implementation |
| ------ | ----------- | -------------- |
| **search** (default) | Paper search & download to Markdown | Script-driven (Semantic Scholar / OpenAlex / arXiv multi-source) |
| **paper** | 12-agent paper writing (10 modes, 6 paper types, 5 citation formats) | Multi-agent |
| **reviewer** | 7-agent multi-perspective peer review (6 modes) | Multi-agent |
| **pipeline** | End-to-end 10-stage workflow (research → writing → integrity → review → revision → final) | Orchestrator |

### Multi-Source Paper Search

- **Semantic Scholar** (primary) → **OpenAlex** (incl. open-access PDFs) → **arXiv** (preprints)
- Supports Crossref (DOI authority) and PubMed (biomedical)
- Free, no API key required, automatic multi-source fallback
- `--source multi` aggregates and deduplicates across three platforms for broadest coverage

### Lossless Paper Conversion

- **LaTeX source path** (preferred): downloads arXiv tarball, Pandoc converts to Markdown, formulas preserved as `$...$` / `$$...$$` (lossless)
- **PDF extraction path** (fallback): pymupdf text extraction + embedded images
- Images auto-extracted to `images/` directory; PDF vector graphics auto-converted to PNG
- Supports DOI / S2 ID reverse lookup for arXiv version to use the lossless path

### Local PDF to Markdown

Standalone interface for converting local PDF files to Markdown, including image extraction.

## Installation

### Option 1: Via `skills` package (recommended)

```bash
# Install to Claude Code
npx skills add Kirky-X/liuxiang --agent claude-code -y

# Install to Trae
npx skills add Kirky-X/liuxiang --agent trae -y
```

### Option 2: Traditional git clone

```bash
git clone https://github.com/Kirky-X/liuxiang.git
# Link or copy SKILL.md + scripts/ + reference/ + agents/ to the agent skills directory
```

### Dependencies

```bash
pip install requests pdfplumber pymupdf httpx beautifulsoup4 lxml pdfminer.six --break-system-packages -q
```

## Usage Examples

### Search papers

```bash
python scripts/search_papers.py "large language model reasoning"
python scripts/search_papers.py "Attention Is All You Need" --mode title
python scripts/search_papers.py "transformer architecture" --source multi --limit 10
```

### Download paper as Markdown

```bash
python scripts/download_paper.py 2310.06825 -o mistral.md
python scripts/download_paper.py 10.1145/3025453.3025717 -o paper.md
```

### Local PDF to Markdown

```bash
python scripts/pdf2md.py ~/papers/attention.pdf -o attention.md
```

## Project Structure

```
liuxiang/
├── SKILL.md              # Skill definition & workflow docs
├── README.md             # Project overview (Chinese)
├── README_EN.md          # Project overview (English)
├── skill.json            # Skill metadata
├── LICENSE               # MIT License
├── scripts/
│   ├── search_papers.py  # Paper search (multi-source aggregation)
│   ├── download_paper.py # Paper download & Markdown conversion
│   ├── pdf2md.py         # Local PDF to Markdown
│   └── html2md.py        # arXiv HTML to Markdown (fallback)
├── reference/            # paper/reviewer/pipeline module workflow docs
├── references/           # API notes & reference materials
├── agents/               # Multi-agent definitions
├── examples/             # Usage examples
└── templates/            # Output templates
```

## License

MIT
