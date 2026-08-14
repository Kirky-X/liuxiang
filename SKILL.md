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
| **search**（默认） | 论文搜索与下载转 Markdown | 脚本驱动（Semantic Scholar / OpenAlex / arXiv / DBLP / Europe PMC / Crossref / PubMed / CORE 多源） | 本文件下方 |
| **paper** | 12-agent 论文写作（full/plan/outline/revision/abstract/lit-review/format-convert/citation-check/disclosure） | 多 agent | [`reference/paper.md`](reference/paper.md) |
| **reviewer** | 7-agent 多视角同行评审（full/re-review/quick/methodology-focus/guided/calibration） | 多 agent | [`reference/reviewer.md`](reference/reviewer.md) |
| **pipeline** | 端到端 10 阶段流水线编排（研究→写作→诚信审查→评审→修订→定稿） | orchestrator 调度 paper/reviewer | [`reference/pipeline.md`](reference/pipeline.md) |

## 模块路由

解析 `$ARGUMENTS[0]`：

- **`search`（或缺失/无效）** → 默认走论文搜索下载，执行本文件下方「search 模块」流程。
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

## search 模块：论文搜索与下载

两个独立脚本接口，分别对应"搜索"和"下载"：

1. `scripts/search_papers.py` — 按主题或标题搜索论文，返回标题、作者、发表时间、摘要等列表
2. `scripts/download_paper.py` — 下载一篇论文并转成 Markdown 文件

搜索数据源（免费无需 Key，多源降级）：Semantic Scholar（主，覆盖广）→ OpenAlex（含开放获取 PDF）→ arXiv（预印本）。还可手动指定 Crossref（DOI 元数据）、PubMed（生物医学）、DBLP（CS 领域权威）、Europe PMC（生物医学全文）、CORE（全球最大 OA 聚合库，需 Key）。下载源见下。详见 [`references/api_notes.md`](references/api_notes.md)。

### 环境准备

首次使用前确认依赖已安装：

```bash
pip install requests pdfplumber pymupdf --break-system-packages -q
```

这两个脚本需要访问外网（`api.semanticscholar.org` / `api.openalex.org` / `api.crossref.org` / `eutils.ncbi.nlm.nih.gov` / `export.arxiv.org` / `arxiv.org` / `dblp.org` / `www.ebi.ac.uk` / `api.core.ac.uk` / `api.unpaywall.org`）。如果当前环境的网络策略不允许访问这些域名（`bash` 报 `host_not_allowed` 或类似拒绝信息），先告知用户，并建议其在允许联网的环境（本地终端 / Claude Code）中运行——不要假装成功或编造结果。

两个脚本内置了瞬时错误重试（429/5xx 自动重试2次，指数退避），单次失败不代表真的不可用，可以先重跑一次。

### 接口一：搜索论文

```bash
python scripts/search_papers.py "<关键词或标题>" [--mode topic|title] [--source auto|multi|semanticscholar|openalex|crossref|pubmed|arxiv|dblp|europmc|core] [--limit 20] [--json]
```

- 主题搜索（默认）：`python scripts/search_papers.py "large language model reasoning"`
- 按论文标题精确查找：`python scripts/search_papers.py "Attention Is All You Need" --mode title`
- **多平台聚合（推荐，覆盖最广）**：`--source multi` 串行查 OpenAlex+Crossref+arXiv+DBLP+Europe PMC，结果合并去重并按来源轮转排序，保证各平台都有代表进入结果，而非单一平台独占前几名。
- 指定单平台：`--source openalex`（含开放 PDF）/ `crossref`（DOI 权威）/ `pubmed`（生物医学）/ `arxiv`（预印本）/ `dblp`（CS 领域权威）/ `europmc`（生物医学全文）/ `core`（全球最大 OA 聚合库，需设置 `CORE_API_KEY` 环境变量）
- 需要程序化处理时用 `--json`，否则默认输出人类可读的列表

`--source auto`（默认）依次尝试 S2→OpenAlex→arXiv，首个非空结果即返回——这样任一平台限流/无数据都不会阻断搜索。`--source multi` 则多平台都查并合并去重，覆盖面更广但耗时更长。默认 `--limit 20`。

每条结果包含：标题、作者、发表时间、来源期刊/venue、arXiv ID / DOI / PMID / Semantic Scholar ID（用于后续下载）、PDF 链接（若可获取）、摘要片段。

**拿到结果后，把列表清晰地展示给用户**（标题+作者+时间+摘要摘要即可，不用把所有字段都堆给用户），并告诉用户可以说"下载第 N 篇"或给出对应的 ID 来触发下载。

### 接口二：下载论文为 Markdown

```bash
python scripts/download_paper.py "<标识符>" -o output.md
```

标识符可以是以下任意一种，脚本会自动识别：

| 类型 | 示例 |
|------|------|
| arXiv ID | `2306.12345`、`arXiv:2306.12345v2`，也支持 2007 年前的旧格式 `hep-th/9901001` |
| Semantic Scholar Paper ID | `649def34f8be52c8b66281af98ae884c09aef38b`（来自搜索结果里的 `semantic_scholar_id`） |
| DOI | `10.1145/3025453.3025717` |
| 直接 PDF 链接 | `https://arxiv.org/pdf/2306.12345` |

流程：解析标识符 → **先反查是否有 arXiv 版本（用户直接给 arXiv ID 时就是它本身；给 DOI / S2 ID 时，从 Semantic Scholar 的 `externalIds.ArXiv` 反查）**→ **有 arXiv 版本则优先下载 LaTeX 源码包并用 Pandoc 转成 Markdown，公式保留为标准 `$...$` / `$$...$$`（无损，结构最完整）；反查不到 arXiv 或只有 PDF（作者未提交源码、或 Pandoc 不可用）时降级用 `pymupdf` 提取 PDF 正文和图片** → 写出包含标题/作者/发表时间/来源/摘要/正文的 Markdown 文件。

**OA PDF 解析链**（DOI 下载时）：Semantic Scholar `openAccessPdf` → Unpaywall（按 DOI 反查 OA 链接，覆盖 1.2 亿+ DOI，需设置 `UNPAYWALL_EMAIL` 环境变量为真实邮箱）→ arXiv PDF。Unpaywall 常能找到 S2 遗漏的机构仓库版本，显著提升 DOI 论文的下载成功率。未设置 `UNPAYWALL_EMAIL` 时自动跳过 Unpaywall，不影响其他路径。

图片处理：两种转换路径均会将图片提取到输出 Markdown 同级的 `images/` 目录，Markdown 中以相对路径引用（如 `![figure](images/fig1.png)`）。LaTeX 源码路径通过 Pandoc 的 `--extract-media` 提取；PDF 路径通过 `pymupdf` 提取嵌入图片（跳过 < 5KB 的小图标，自动去重）。

这意味着用 DOI / S2 ID 下载时，只要该论文有 arXiv 预印本（CS/AI/物理/数学领域已发表论文命中率很高），同样能走 LaTeX 无损路径，且元信息保留正式发表版（venue 显示真实期刊/会议，而非 arXiv）。

输出的 Markdown 会标注「转换方式」：`LaTeX 源码 → Markdown`（公式完整）或 `PDF 文本提取`（公式可能退化）。

#### 备用转换器：arXiv HTML/PDF 手动转换

`download_paper.py` 主路径依赖 `pypandoc-binary`（LaTeX 源码 + Pandoc）。当 Pandoc 不可用、或需要从 arXiv 的 HTML（LaTeXML）版本提取公式时，可用以下两个独立转换器作为备用路径：

```bash
# 1. 先拉取 arXiv HTML 版本（LaTeXML 结构化页面，公式以 LaTeX 源码保存）
python3 -c "import httpx; open('paper.html','wb').write(httpx.get('https://arxiv.org/html/<paper_id>v1', follow_redirects=True).content)"

# 2. HTML → Markdown（从 <annotation encoding="application/x-tex"> 提取 LaTeX，公式保留为 $...$ / $$...$$）
python3 scripts/html2md.py paper.html <paper_id> --output paper.md

# 3. 或强制走 PDF 路径（自动链 pandoc → pdfminer.six → pdftotext → 原始文本）
python3 scripts/pdf2md.py paper.pdf <paper_id> --output paper.md
```

- **`scripts/html2md.py`**：BeautifulSoup + lxml 递归树遍历，从 LaTeXML 结构化 HTML 提取章节、公式（行内 `$...$` / 块级 `$$...$$`）、图片（相对路径转绝对 URL）、表格、参考文献。优先从 `<annotation encoding="application/x-tex">` 取 LaTeX 源码，后备从 `alttext` 属性。质量优于 PDF 文本提取，是 Pandoc 不可用时保留公式的首选后备。
- **`scripts/pdf2md.py`**：多后端 PDF→Markdown 链（优先级：pandoc → pymupdf → pdfminer.six → pdftotext → 原始文本），含章节推断启发式（识别 "Abstract"/"Introduction"/"1." 等标题模式）。pymupdf 路径会同时提取嵌入图片到 `images/` 目录。纯文本保底会丢失公式和图片，仅作最后手段。
- **何时用这些备用转换器**：主路径 `download_paper.py` 已能处理绝大多数情况；仅当 (a) Pandoc 未安装且想保留公式 → 用 `html2md.py`；(b) 想手动控制转换过程或调试输出质量 → 单独调用。

依赖：`pip install httpx beautifulsoup4 lxml pdfminer.six pymupdf`（pandoc / pdftotext 为可选系统命令）。

### 接口三：本地 PDF 转 Markdown

将本地 PDF 文件转换为 Markdown，支持图片提取。适用于用户有自己的 PDF 论文需要转换的场景。

```bash
python scripts/pdf2md.py <pdf文件路径或URL> [paper_id] [--output output.md]
```

- 转换本地 PDF：`python scripts/pdf2md.py ~/papers/attention.pdf -o attention.md`
- 转换 URL PDF：`python scripts/pdf2md.py https://arxiv.org/pdf/2306.12345 2306.12345 -o paper.md`
- `paper_id` 可选，未提供时从文件名自动推导
- 图片提取到输出文件同级的 `images/` 目录，Markdown 中以相对路径引用
- 转换后端优先级：pandoc（含 `--extract-media`）→ pymupdf（文本+图片）→ pdfminer.six → pdftotext → 原始文本

**重要限制**：只有"开放获取"（open access）的论文才能下载全文。如果一篇论文没有免费 PDF（比如很多期刊付费墙文章），脚本会报错并说明原因——这种情况下可以把接口一返回的摘要信息直接整理给用户，不要假装下载成功。

下载完成后用 `present_files` 把生成的 `.md` 文件交给用户，不要只在对话里贴一遍全文。

### 典型工作流程

用户说"帮我找几篇关于 XX 的论文" → 调用接口一 → 展示列表 → 用户选中某一篇或直接说"下载这篇" → 调用接口二，标识符用列表里对应的 arXiv ID / DOI / S2 ID → 呈现生成的 Markdown 文件。

用户直接给出论文标题或链接要下载 → 可以先用接口一按标题搜索确认是哪一篇、拿到规范的 ID，再调用接口二下载；如果用户直接给了 arXiv ID/DOI/PDF 链接，可以跳过搜索直接下载。

### 已知局限

- **PDF 提取路径（降级时）无法保留 LaTeX 公式**：数学符号会退化成纯文本、双栏排版可能交错。无论用户给的是 arXiv ID、DOI 还是 S2 ID，只要反查到 arXiv 版本就优先走 LaTeX 源码路径避免此问题；Pandoc 不可用时可用上面的 `html2md.py` 从 HTML 版本提取公式（备用转换器），仅当论文确实没有 arXiv 版本且只有付费/无源 PDF 时才会降级到 PDF 提取，此时公式质量有限。

- 扫描版 PDF（图片型，无文字层）提取不出正文，只能拿到标题/摘要，需要额外 OCR。
- Semantic Scholar 无 Key 时是共享限流池，短时间大量请求可能被限速；`search_papers.py` 在其失败时会自动降级到 arXiv。
- arXiv 只覆盖预印本，搜不到已发表期刊论文的最终版；这种情况下换回 Semantic Scholar 或直接给 DOI。
- 更多 API 细节（字段含义、错误处理、限流数值）见 [`references/api_notes.md`](references/api_notes.md)，一般不需要主动读，除非遇到报错需要排查。
