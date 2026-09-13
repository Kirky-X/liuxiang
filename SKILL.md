---
name: liuxiang
description: >
  学术研究全流程套件。四个模块：search（论文搜索与下载，脚本驱动，默认）、paper（12-agent 论文写作，10 模式，6 论文类型，5 引用格式，双语摘要，LaTeX/DOCX/PDF 输出）、reviewer（7-agent 多视角同行评审，6 模式）、pipeline（端到端 10 阶段流水线：研究→写作→诚信审查→同行评审→修订→定稿）。触发：搜论文/找论文/下载论文/arXiv/DOI/写论文/评审论文/peer review/学术流水线。$ARGUMENTS[0] 选模块，无参默认走 search 模块。
argument-hint: "[search|paper|reviewer|pipeline] ..."
---

# 学术研究全流程套件

四个模块的统一入口，覆盖从文献检索到论文定稿的完整学术生命周期。

| 模块 | 功能 | 实现 | 流程文档 |
| ---- | ---- | ---- | -------- |
| **search**（默认） | 论文搜索与下载转 Markdown | 脚本驱动（Semantic Scholar / OpenAlex / arXiv / DBLP / Europe PMC / Crossref / PubMed / CORE 多源） | [`reference/search.md`](reference/search.md) |
| **paper** | 12-agent 论文写作（full/plan/outline/revision/abstract/lit-review/format-convert/citation-check/disclosure） | 多 agent | [`reference/paper.md`](reference/paper.md) |
| **reviewer** | 7-agent 多视角同行评审（full/re-review/quick/methodology-focus/guided/calibration） | 多 agent | [`reference/reviewer.md`](reference/reviewer.md) |
| **pipeline** | 端到端 10 阶段流水线编排（研究→写作→诚信审查→评审→修订→定稿） | orchestrator 调度 paper/reviewer | [`reference/pipeline.md`](reference/pipeline.md) |

## 模块路由

解析 `$ARGUMENTS[0]`：

- **`search`（或缺失/无效）** → 默认走论文搜索下载，读 [`reference/search.md`](reference/search.md) 执行。
- **`paper`** → 读 [`reference/paper.md`](reference/paper.md)，`$ARGUMENTS[1]` 作模式（默认 `full`），执行写作。
- **`reviewer`** → 读 [`reference/reviewer.md`](reference/reviewer.md)，`$ARGUMENTS[1]` 作模式（默认 `full`），执行评审。
- **`pipeline`（或 `full`）** → 读 [`reference/pipeline.md`](reference/pipeline.md)，执行 10 阶段流水线，orchestrator 在各阶段内部调度 paper/reviewer 模块。

各 `reference/<module>.md` 内对 `agents/`、`references/`、`examples/`、`templates/` 的引用在本技能根目录下解析，路径自洽。

### 模块协作链路

```
search (检索下载原始论文) → paper (写作) → integrity 审查 → reviewer (评审)
  → paper (修订) → reviewer (re-review) → 最终 integrity → 定稿
```

`pipeline` 模块编排上述全链路（10 阶段 + 强制诚信审查 + 两阶段评审）。

---

## search 模块速览（3 条核心命令）

详细用法（数据源选择、标识符类型、备用转换器、已知局限、handoff 格式）**Read [`reference/search.md`](reference/search.md)**。

```bash
# 1. 搜索论文（多源聚合推荐）
python3 scripts/search_papers.py "<关键词或标题>" --source multi --limit 20 --json

# 2. 下载一篇论文并转成 Markdown（arXiv ID / DOI / S2 ID / PDF 链接均可）
python3 scripts/download_paper.py "2306.12345" -o paper.md

# 3. 本地 PDF 转 Markdown
python3 scripts/pdf2md.py <pdf文件路径> -o output.md
```

要点：只有开放获取论文能下载全文，拿不到全文时把搜索返回的摘要整理给用户，不要编造结果；搜索结果列表要清晰展示给用户，并提示可以说"下载第 N 篇"。

### 与其他模块的衔接

search 产物（Markdown 全文清单，每篇含标题/来源/本地路径）是 paper 模块 Phase 1 `literature_strategist_agent` 与 pipeline 模块 Stage 1 的输入语料，交接格式见 [`reference/search.md`](reference/search.md) §「与其他模块的衔接」。
