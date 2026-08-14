# Liuxiang — Academic Research Suite

[中文](README.md)

[![GitHub Release](https://img.shields.io/github/v/release/Kirky-X/liuxiang?style=flat-square)](https://github.com/Kirky-X/liuxiang/releases) [![GitHub License](https://img.shields.io/github/license/Kirky-X/liuxiang?style=flat-square)](LICENSE)

Liuxiang is an AI agent skill for the full academic research lifecycle — from literature search to paper finalization. Four independent yet composable modules cover multi-source paper discovery, lossless LaTeX/PDF conversion, multi-agent paper writing, and peer review.

## Modules

| Module | Description | Implementation |
| ------ | ----------- | -------------- |
| **search** (default) | Paper search & download to Markdown | Script-driven (Semantic Scholar / OpenAlex / arXiv) |
| **paper** | 12-agent paper writing (10 modes, 6 paper types, 5 citation formats) | Multi-agent |
| **reviewer** | 7-agent multi-perspective peer review (6 modes) | Multi-agent |
| **pipeline** | End-to-end 10-stage workflow (research → writing → integrity → review → revision → final) | Orchestrator |

## Installation

```bash
# Via skills CLI (recommended)
npx skills add Kirky-X/liuxiang --agent claude-code -y

# Traditional clone
git clone https://github.com/Kirky-X/liuxiang.git
```

### Dependencies

```bash
pip install requests pdfplumber pymupdf httpx beautifulsoup4 lxml pdfminer.six --break-system-packages -q
```

## Usage

### Search papers

```bash
python scripts/search_papers.py "large language model reasoning"
python scripts/search_papers.py "Attention Is All You Need" --mode title
```

### Download paper as Markdown

```bash
python scripts/download_paper.py 2310.06825 -o mistral.md
```

### Local PDF to Markdown

```bash
python scripts/pdf2md.py ~/papers/attention.pdf -o attention.md
```

## License

MIT
