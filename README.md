# Liuxiang (刘向) —— 学术研究全流程套件

中文 | [English](README_EN.md)

[![GitHub Release](https://img.shields.io/github/v/release/Kirky-X/liuxiang?style=flat-square)](https://github.com/Kirky-X/liuxiang/releases) [![GitHub License](https://img.shields.io/github/license/Kirky-X/liuxiang?style=flat-square)](LICENSE)

Liuxiang 是面向 AI agent 的学术研究全流程 skill，覆盖从文献检索到论文定稿的完整学术生命周期。四个模块各自独立又可协同编排，支持多数据源论文搜索、LaTeX/PDF 双路径无损转换、多 agent 论文写作与同行评审。

## 功能特性

### 四大模块

| 模块 | 功能 | 实现 |
| ---- | ---- | ---- |
| **search**（默认） | 论文搜索与下载转 Markdown | 脚本驱动（Semantic Scholar / OpenAlex / arXiv 多源） |
| **paper** | 12-agent 论文写作（10 模式，6 论文类型，5 引用格式） | 多 agent |
| **reviewer** | 7-agent 多视角同行评审（6 模式） | 多 agent |
| **pipeline** | 端到端 10 阶段流水线（研究→写作→诚信审查→评审→修订→定稿） | orchestrator 调度 |

### 多数据源论文搜索

- **Semantic Scholar**（主）→ **OpenAlex**（含开放获取 PDF）→ **arXiv**（预印本）
- 支持 Crossref（DOI 权威）、PubMed（生物医学）
- 免费无需 API Key，多源自动降级
- `--source multi` 三平台聚合去重，覆盖最广

### 无损论文转换

- **LaTeX 源码路径**（优先）：下载 arXiv tarball，Pandoc 转 Markdown，公式保留 `$...$` / `$$...$$`（无损）
- **PDF 提取路径**（降级）：pymupdf 提取文本 + 嵌入图片
- 图片自动提取到 `images/` 目录，PDF 矢量图自动转 PNG
- 支持 DOI / S2 ID 反查 arXiv 版本走无损路径

### 本地 PDF 转 Markdown

独立接口，支持将本地 PDF 文件转换为 Markdown，含图片提取。

## 安装

### 方式一：通过 `skills` 包安装（推荐）

```bash
# 安装到 Claude Code
npx skills add Kirky-X/liuxiang --agent claude-code -y

# 安装到 Trae
npx skills add Kirky-X/liuxiang --agent trae -y
```

### 方式二：传统 git clone

```bash
git clone https://github.com/Kirky-X/liuxiang.git
# 将 SKILL.md + scripts/ + reference/ + agents/ 链接或复制到 agent skills 目录
```

### 环境依赖

```bash
pip install requests pdfplumber pymupdf httpx beautifulsoup4 lxml pdfminer.six --break-system-packages -q
```

## 使用示例

### 搜索论文

```bash
python scripts/search_papers.py "large language model reasoning"
python scripts/search_papers.py "Attention Is All You Need" --mode title
python scripts/search_papers.py "transformer architecture" --source multi --limit 10
```

### 下载论文为 Markdown

```bash
python scripts/download_paper.py 2310.06825 -o mistral.md
python scripts/download_paper.py 10.1145/3025453.3025717 -o paper.md
```

### 本地 PDF 转 Markdown

```bash
python scripts/pdf2md.py ~/papers/attention.pdf -o attention.md
```

## 项目结构

```
liuxiang/
├── SKILL.md              # 技能定义与流程文档
├── README.md             # 项目说明（中文）
├── README_EN.md          # 项目说明（英文）
├── skill.json            # 技能元数据
├── LICENSE               # MIT 许可证
├── scripts/
│   ├── search_papers.py  # 论文搜索（多源聚合）
│   ├── download_paper.py # 论文下载与 Markdown 转换
│   ├── pdf2md.py         # 本地 PDF 转 Markdown
│   └── html2md.py        # arXiv HTML 转 Markdown（备用）
├── reference/            # paper/reviewer/pipeline 模块流程文档
├── references/           # API 笔记与参考资料
├── agents/               # 多 agent 定义
├── examples/             # 使用示例
└── templates/            # 输出模板
```

## 许可证

MIT
