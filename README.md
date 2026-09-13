# Liuxiang (刘向) — 学术研究全流程套件

> 覆盖从文献检索到论文定稿完整生命周期的 AI agent skill：论文搜索下载（脚本驱动）、12-agent 论文写作、7-agent 同行评审、端到端流水线编排，四个模块独立可用亦可协同。

[![Version](https://img.shields.io/badge/dynamic/yaml?url=https%3A%2F%2Fraw.githubusercontent.com%2FKirky-X%2Fliuxiang%2Fmain%2Fskill.json&query=%24.version&label=version&style=flat-square)](https://github.com/Kirky-X/liuxiang/releases) [![GitHub Release](https://img.shields.io/github/v/release/Kirky-X/liuxiang?style=flat-square)](https://github.com/Kirky-X/liuxiang/releases) [![GitHub License](https://img.shields.io/github/license/Kirky-X/liuxiang?style=flat-square)](LICENSE)

中文 | [English](README_EN.md)

## ✨ 功能特性

**四个模块**（`$ARGUMENTS[0]` 选模块，无参默认 search）：

| 模块 | 功能 | 实测规模 |
| ---- | ---- | ---- |
| **search**（默认） | 论文搜索与下载转 Markdown，脚本驱动 | 8 个数据源：Semantic Scholar / OpenAlex / arXiv / DBLP / Europe PMC / Crossref / PubMed / CORE，`--source multi` 聚合去重，多源自动降级 |
| **paper** | 12-agent 论文写作 | 10 种模式（full / plan / outline / revision / abstract / lit-review / format-convert / citation-check / disclosure 等）、6 论文类型、5 引用格式、双语摘要，LaTeX/DOCX/PDF 输出 |
| **reviewer** | 7-agent 多视角同行评审 | 6 种模式（full / re-review / quick / methodology-focus / guided / calibration） |
| **pipeline** | 端到端 10 阶段流水线 | 研究→写作→诚信审查→评审→修订→定稿，orchestrator 调度 paper/reviewer |

- **无损转换**：下载优先走 arXiv LaTeX 源码路径（tarball → Pandoc，公式保留 `$...$`/`$$...$$`），失败降级 PDF 提取（pymupdf），再降级 arXiv HTML 备用转换器；DOI / S2 ID 自动反查 arXiv 版本
- **安全加固**：`download_paper.py` 带 SSRF 防护（scheme 白名单 + 拒绝解析到内网/链路本地的目标）与 tar 安全解压（拒绝路径穿越、symlink、非普通文件成员）
- **修后状态**：SKILL.md 瘦身至 3.8KB，search 详细用法外置 `reference/search.md`；约 130 处悬空引用已处理——90 处改指真实资产，其余 49 处（13 个文件）显式标注「⚠️ 依赖缺失，当前版本未实现」（上游 ARS 的 shared 契约、compliance/raise 框架等无等价物），未标注残留为 0
- **search → paper/pipeline 衔接**：search 产物（Markdown 全文清单）是 paper 模块文献策略 agent 与 pipeline Stage 1 的输入语料，交接格式见 `reference/search.md` §「与其他模块的衔接」

## 📦 安装

```bash
# 方式一：从本工作区统一部署（部署到 ~/.zcode/skills 与 ~/.claude/skills）
bash scripts/sync-skills.sh liuxiang

# 方式二：手动复制到 ZCode 技能目录
cp -r /path/to/liuxiang ~/.zcode/skills/liuxiang

# 方式三：远程安装（GitHub 仓库）
npx skills add Kirky-X/liuxiang --agent claude-code -y
```

依赖：Python 3.8+ 与 `requests httpx beautifulsoup4 lxml pdfminer.six pymupdf`（`pip install` 即可，搜索类 API 免费、无需 Key）；Pandoc 为 LaTeX 无损路径的可选依赖。

## 🚀 快速开始

```bash
# 1. 搜索论文（多源聚合；实测 Semantic Scholar 限流 429 时自动降级 OpenAlex 出结果）
python3 scripts/search_papers.py "large language model reasoning" --source multi --limit 20 --json

# 2. 下载一篇论文转 Markdown（arXiv ID / DOI / S2 ID / PDF 链接均可）
python3 scripts/download_paper.py "1706.03762" -o attention.md

# 3. 本地 PDF 转 Markdown（含图片提取）
python3 scripts/pdf2md.py ~/papers/attention.pdf -o attention.md

# agent 内调用：/liuxiang（默认 search）、/liuxiang paper full、/liuxiang reviewer quick、/liuxiang pipeline
```

注意：只有开放获取论文能下载全文；拿不到全文时把搜索返回的摘要整理给用户，不编造结果。

## ✅ 测试与验证

2026-09-13 实测（v0.1.1，与 git tag 一致）：

- **语法**：4 个 Python 脚本 `py_compile` 全部通过
- **功能**：
  - `search_papers.py "attention is all you need" --mode title --limit 3` 真实返回 3 条结果（Semantic Scholar 429 → 自动降级 OpenAlex）
  - `pdf2md.py` 对本地生成的 PDF 端到端转换成功，输出含 frontmatter 与正文
  - `download_paper.py 1706.03762` 在本环境因 arXiv 连接被重置未能完成下载；脚本的 LaTeX→PDF 降级链与错误提示按预期工作（arXiv 可达环境可完整走通）
- **安全**：SSRF 防护与 tar 安全解压代码在位（`download_paper.py`，修复报告记录 7/7 用例通过）
- liuxiang 自带 CI（`.github/workflows/`：ci.yml / codeql.yml / release.yml）

## 📁 目录结构

```
liuxiang/
├── SKILL.md            # 3.8KB 入口：四模块路由 + search 速览
├── skill.json          # v0.1.1, MIT
├── scripts/            # search_papers.py / download_paper.py / pdf2md.py / html2md.py
├── reference/          # 四模块流程文档（search / paper / reviewer / pipeline）
├── references/         # 58 篇协议与规范（引用格式 / 评审标准 / 流水线状态机 …）
├── agents/             # 24 个 agent 定义（paper 12 + reviewer 7 + orchestrator 等）
├── templates/          # 14 个输出模板（IMRaD / 评审报告 / 修订跟踪 …）
└── examples/           # 15 个示例（完整流水线 / 修订恢复 / 文献综述 …）
```

## 🔮 边界

- **search 模块**：免费公开 API，无 API Key 需求；Semantic Scholar 共享限流池，高频请求可能 429（脚本自动换源）
- **不触发**：与学术研究无关的写作/检索请求；paper 模块只在明确的论文写作意图时进入
- **与兄弟 skill 分工**：`cangjie` 做通用内容转化与笔记；`diting` 做通用代码质量审查；liuxiang 的 reviewer 是学术同行评审（多视角评分 + 修订路线图），pipeline 只编排学术生命周期
- **已知局限**：详见 `reference/search.md` §「已知局限」；上游机制缺失项均以「⚠️ 依赖缺失」标注（见功能特性）

## 📄 License 与归属

本套件 MIT License（作者 Kirky-X）。paper / reviewer / pipeline 模块的 reference 文档与 agents 定义源自上游 ARS 项目 [Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills)（© 2026 Cheng-I Wu，采用 **CC BY-NC 4.0** 授权，非标准 SPDX 许可）；按该授权现状如实标注，上游共享资产（shared 契约文件等）未随本套件发布。
