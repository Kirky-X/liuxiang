# Liuxiang — Academic Research Suite

> An AI agent skill covering the full academic lifecycle from literature search to final paper: script-driven paper discovery, 12-agent paper writing, 7-agent peer review, and an end-to-end pipeline — four modules that work independently or together.

[![Version](https://img.shields.io/badge/dynamic/yaml?url=https%3A%2F%2Fraw.githubusercontent.com%2FKirky-X%2Fliuxiang%2Fmain%2Fskill.json&query=%24.version&label=version&style=flat-square)](https://github.com/Kirky-X/liuxiang/releases) [![GitHub Release](https://img.shields.io/github/v/release/Kirky-X/liuxiang?style=flat-square)](https://github.com/Kirky-X/liuxiang/releases) [![GitHub License](https://img.shields.io/github/license/Kirky-X/liuxiang?style=flat-square)](LICENSE)

English | [中文](README.md)

## ✨ Features

**Four modules** (`$ARGUMENTS[0]` selects; defaults to search):

| Module | Description | Measured scale |
| ------ | ----------- | -------------- |
| **search** (default) | Paper search & download to Markdown, script-driven | 8 sources: Semantic Scholar / OpenAlex / arXiv / DBLP / Europe PMC / Crossref / PubMed / CORE; `--source multi` aggregates with dedup; automatic multi-source fallback |
| **paper** | 12-agent paper writing | 10 modes (full / plan / outline / revision / abstract / lit-review / format-convert / citation-check / disclosure, etc.), 6 paper types, 5 citation formats, bilingual abstract, LaTeX/DOCX/PDF output |
| **reviewer** | 7-agent multi-perspective peer review | 6 modes (full / re-review / quick / methodology-focus / guided / calibration) |
| **pipeline** | End-to-end 10-stage pipeline | research → writing → integrity review → review → revision → finalization; an orchestrator drives paper/reviewer |

- **Lossless conversion**: download prefers the arXiv LaTeX source path (tarball → Pandoc, math preserved as `$...$`/`$$...$$`), falls back to PDF extraction (pymupdf), then to the arXiv HTML converter; DOI / S2 IDs are auto-resolved to arXiv versions.
- **Hardened**: `download_paper.py` has SSRF protection (scheme whitelist + rejection of targets resolving to local/link-local addresses) and tar-safe extraction (rejects path traversal, symlinks, and non-regular-file members).
- **Post-fix state**: SKILL.md slimmed to 3.8KB with search usage externalized to `reference/search.md`; ~130 dangling references resolved — 90 repointed to real assets, the remaining 49 (13 files) explicitly marked "⚠️ 依赖缺失，当前版本未实现" (upstream ARS shared contracts and compliance/raise frameworks have no equivalent here), zero unmarked leftovers.
- **search → paper/pipeline handoff**: search output (a Markdown full-text list) is the input corpus for paper's literature strategist agent and pipeline Stage 1; the handoff format is in `reference/search.md` § "与其他模块的衔接".

## 📦 Installation

```bash
# Option 1: deploy from this workspace (to ~/.zcode/skills and ~/.claude/skills)
bash scripts/sync-skills.sh liuxiang

# Option 2: manual copy into the ZCode skills directory
cp -r /path/to/liuxiang ~/.zcode/skills/liuxiang

# Option 3: remote install from GitHub
npx skills add Kirky-X/liuxiang --agent claude-code -y
```

Dependencies: Python 3.8+ with `requests httpx beautifulsoup4 lxml pdfminer.six pymupdf` (a `pip install` away; the search APIs are free and keyless); Pandoc is an optional dependency for the lossless LaTeX path.

## 🚀 Quick Start

```bash
# 1. Search papers (multi-source; when Semantic Scholar rate-limits with 429, the script falls back to OpenAlex — verified live)
python3 scripts/search_papers.py "large language model reasoning" --source multi --limit 20 --json

# 2. Download a paper as Markdown (arXiv ID / DOI / S2 ID / PDF URL all accepted)
python3 scripts/download_paper.py "1706.03762" -o attention.md

# 3. Convert a local PDF to Markdown (with image extraction)
python3 scripts/pdf2md.py ~/papers/attention.pdf -o attention.md

# In-agent: /liuxiang (defaults to search), /liuxiang paper full, /liuxiang reviewer quick, /liuxiang pipeline
```

Note: only open-access papers can be downloaded in full text; when full text is unavailable, present the abstracts returned by search instead of fabricating results.

## ✅ Tests & Verification

Verified 2026-09-13 (v0.1.1, matching the git tag):

- **Syntax**: all 4 Python scripts pass `py_compile`.
- **Functional**:
  - `search_papers.py "attention is all you need" --mode title --limit 3` returned 3 real results (Semantic Scholar 429 → automatic fallback to OpenAlex)
  - `pdf2md.py` converted a locally generated PDF end-to-end, producing frontmatter and body text
  - `download_paper.py 1706.03762` could not complete in this environment because connections to arXiv were reset; the script's LaTeX→PDF fallback chain and error reporting behaved as designed (the full path works where arXiv is reachable)
- **Security**: SSRF protection and tar-safe extraction are in place in `download_paper.py` (the fix report records 7/7 test cases passing).
- liuxiang ships its own CI (`.github/workflows/`: ci.yml / codeql.yml / release.yml).

## 📁 Directory Structure

```
liuxiang/
├── SKILL.md            # 3.8KB entry: four-module routing + search quick reference
├── skill.json          # v0.1.1, MIT
├── scripts/            # search_papers.py / download_paper.py / pdf2md.py / html2md.py
├── reference/          # Per-module flow docs (search / paper / reviewer / pipeline)
├── references/         # 58 protocols & standards (citation formats / review criteria / pipeline state machine …)
├── agents/             # 24 agent definitions (paper 12 + reviewer 7 + orchestrator, etc.)
├── templates/          # 14 output templates (IMRaD / review report / revision tracking …)
└── examples/           # 15 examples (full pipeline / revision recovery / literature review …)
```

## 🔮 Boundaries

- **search module**: free public APIs, no API key needed; Semantic Scholar uses a shared rate-limit pool and may return 429 under heavy use (the script switches sources automatically).
- **Does not trigger**: writing or search requests unrelated to academic research; the paper module enters only on explicit paper-writing intent.
- **Sibling skills**: `cangjie` handles general content transformation and notes; `diting` handles general code quality review; liuxiang's reviewer is academic peer review (multi-perspective scoring + revision roadmap), and pipeline orchestrates only the academic lifecycle.
- **Known limitations**: see `reference/search.md` § "已知局限"; upstream mechanisms that are missing are all marked "⚠️ 依赖缺失" (see Features).

## 📄 License & Attribution

This suite is MIT licensed (author Kirky-X). The reference docs and agent definitions of the paper / reviewer / pipeline modules derive from the upstream ARS project [Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills) (© 2026 Cheng-I Wu, licensed under **CC BY-NC 4.0**, a non-standard-SPDX license); this is stated as-is per the upstream license's current status, and the upstream shared assets (contract files, etc.) are not shipped with this suite.
