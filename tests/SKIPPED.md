# SKIPPED — 冒烟级离线测试未覆盖项说明

原则：网络请求、外部二进制（pandoc/pdftotext）、真实抓取与转换属副作用，不写假测试。
以下为有意跳过的部分及原因；已覆盖部分均离线可跑（依赖 requests/defusedxml/bs4/lxml/pymupdf
在本环境可用，测试不安装任何新依赖）。

## search_papers.py

- `search_*` 各平台的真实 HTTP 拉取（Semantic Scholar/OpenAlex/Crossref/PubMed/DBLP/
  Europe PMC/CORE）：网络副作用。已改为 mock `_get_with_retry` 覆盖查询构造（arXiv
  title/topic 语法）与各平台响应字段映射（S2/DBLP 含 dict 单作者等异形结构）。
- `search_core` 需真实 `CORE_API_KEY`，未设置时直接抛错，不做在线验证。
- 真实 429 限流行为不可离线复现，重试逻辑用 mock 响应覆盖（429→200 重试、
  连续失败抛最后异常）。

## download_paper.py

- 真实下载链路（arXiv e-print/PDF、S2 元数据、Unpaywall 反查）：网络副作用。
  仅通过 env 把 S2 端点指向拒绝连接的本地端口，离线验证「S2 兜底标识符查不到 → 报错退出 1」。
- `latex_source_to_markdown` / `pypandoc` LaTeX→Markdown 全链路：需真实 LaTeX 源码包与
  pandoc 二进制；其纯文本子步骤（`\input` 递归展开、公式定界符规范化、div 噪音清理、
  markdown 组装）已离线覆盖。
- `pdf_to_markdown_body` 真实 PDF 解析：已在 pdf2md 一侧用 pymupdf 生成的 PDF 覆盖
  同源能力（文本提取与图片提取），不重复造网络下载场景。

## pdf2md.py

- `convert()` 多后端真实转换（pandoc/pdfminer/pdftotext）：依赖外部二进制与第三方包的
  真实行为，冒烟不测；其纯函数层（TOC 删除、文本清理、结构启发式、frontmatter 组装）
  与 pymupdf 图片提取（含 <5KB 图标跳过、同图去重）已覆盖。
- URL 方式真实下载 PDF：网络副作用，仅测 scheme 白名单拒绝（file:///ftp://）。

## html2md.py

- 无跳过项：bs4+lxml 离线可用，已用构造的 LaTeXML 风格 HTML 做端到端转换测试
  （frontmatter/摘要/公式/图/表/列表/参考文献/abs 页 meta 合并）。
- 真实 arXiv HTML 页面的抓取本身不在脚本职责内（脚本只做本地文件转换），无需网络。

## 覆盖口径

- 覆盖：纯函数真实行为、响应解析与查询构造（mock HTTP 层）、SSRF 防护
  （含 DNS 解析结果 mock）、tar 安全解压（路径穿越/symlink/绝对路径拒绝）、
  CLI `--help` 与参数校验退出码（子进程冒烟）。
- 跳过：任何真实网络请求与外部二进制转换路径（原因见上）。
- 本仓 scripts 与外部 deep-research 仓存在跨仓引用，属合法引用，未做任何改动。
