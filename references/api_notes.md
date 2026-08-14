# API 细节参考

只有在排查报错、需要调整脚本行为，或者用户明确要求扩展到其它数据源时才需要读这份文档。

## Semantic Scholar（主搜索源）

- 端点：`GET https://api.semanticscholar.org/graph/v1/paper/search`
- 无需 API Key，共享限流池；短时间大量请求可能收到 429，可加 `time.sleep(1)` 重试或换成带 Key 的请求（`headers={"x-api-key": key}`，1 RPS）。
- 常用 `fields`：`title,authors,year,publicationDate,abstract,externalIds,openAccessPdf,venue,url`
- `externalIds` 里可能包含 `DOI`、`ArXiv`、`PubMed` 等，`openAccessPdf.url` 是免费全文链接（没有则说明该论文不开放获取）。**`externalIds.ArXiv` 是「DOI/S2 ID 反查 arXiv 版本」的关键**：用户给 DOI 或 S2 ID 下载时，若这里返回了 ArXiv ID，`download_paper.py` 会自动用该 ID 走 arXiv LaTeX 无损路径（多数 CS/AI 顶会论文都有 arXiv 预印本，命中率很高）。
- 按 ID 查询：`GET /graph/v1/paper/{paper_id}`，`{paper_id}` 支持裸 Semantic Scholar ID，也支持 `DOI:10.xxx`、`ArXiv:2306.12345` 这种前缀写法。
- 批量/大规模抓取用 `/graph/v1/paper/search/bulk`（支持 `token` 翻页，一次最多拿完整数据集，适合科研级批量下载而不是交互式搜索）。
- 推荐论文：`POST /recommendations/v1/papers`，传 `positivePaperIds`/`negativePaperIds`。

## OpenAlex（搜索源：覆盖最广的开放学术图谱）

- 端点：`GET https://api.openalex.org/works`，免费、无需 Key（2026.2 起需免费 Key）。
- 带 `mailto` 参数进入“礼貌用户池”享更高速率；脚本通过 `PAPER_SEARCH_EMAIL` 环境变量注入。
- 搜索：`?search=<关键词>&per_page=N&select=<字段列表>`。
- **对下载最有价值**：返回 `open_access.oa_url`（开放获取 PDF 直链）和 `doi`，拿到的 DOI 能直接走 `download_paper.py` 的 arXiv 反查 LaTeX 路径。
- 摘要格式是倒排索引（`abstract_inverted_index`），脚本已还原成文本。
- `primary_location.source.display_name` 是期刊/会议名（venue）。

## Crossref（搜索源：DOI 权威元数据）

- 端点：`GET https://api.crossref.org/works`，免费、无需 Key，50 RPS。
- 带 `mailto` 进礼貌池。搜索：`?query.bibliographic=<关键词>&rows=N`。
- 覆盖所有正式发表论文（期刊/会议/书籍），`DOI` 字段最权威；`container-title[0]` 是 venue。
- 摘要常含 JATS XML 标签（`<jats:p>` 等），脚本已用 `re.sub(r"<[^>]+>", "")` 净化。
- 不含预印本，但拿到的 DOI 可反查 arXiv 走 LaTeX 路径。

## PubMed E-utilities（搜索源：生物医学）

- 两步式：`GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi` 拿 PMID 列表 → `GET .../esummary.fcgi` 批量取详情。免费、无需 Key，建议 3 RPS。
- 返回 PMID（`articleids` 里也可能有 DOI），`fulljournalname` 是 venue。
- **esummary 不含摘要**（需额外 efetch，脚本省略以免多一次请求影响交互搜索速度）。
- 领域偏生物医学；拿到 DOI 后同样可走下载接口。

## arXiv（搜索源 + 下载来源）

- 端点：`GET https://export.arxiv.org/api/query`，返回 Atom feed（XML），无需注册。（必须用 https，http 会被 301 重定向到 https 且 requests 跟随时偶发读超时。）
- 查询前缀：`ti:`标题 `au:`作者 `abs:`摘要 `cat:`分类（如 `cs.AI`）`all:`全字段。多词查询用 `AND` 连接（如 `all:intent AND all:detection`），不要用 `all:"词1 词2"` 短语查询——arXiv 短语查询要求词序完全一致，多词几乎必然 0 命中。
- 限流建议：请求间隔 ≥3 秒；单次最多 2000 条，累计最多 300,000 条。当前脚本只做单次搜索，不涉及翻页,不需要额外限流。
- PDF 直链固定格式：`https://arxiv.org/pdf/<arxiv_id>`，不需要额外查询，这也是 `download_paper.py` 对 arXiv ID 的兜底下载逻辑。
- **LaTeX 源码端点**：`https://arxiv.org/e-print/<arxiv_id>`，返回 gzip 压缩的 tar 包（`Content-Type: application/gzip`），内含论文原始 `.tex` 文件、`.bib` 参考文献、图片等。绝大多数 arXiv 论文都有源码（作者提交时 arXiv 鼓励上传源码）。`download_paper.py` 优先用此端点拿源码，再通过 Pandoc 转 Markdown，以无损保留公式（`$...$` / `$$...$$`）。少数论文作者只提交 PDF（此时 e-print 返回 `Content-Type: application/pdf`），脚本会自动降级到 PDF 文本提取。
- **DOI / S2 ID 反查 arXiv**：`download_paper.py` 不限于用户直接给 arXiv ID——给 DOI 或 S2 ID 时，会先查 Semantic Scholar 的 `externalIds.ArXiv`，有则用该 ID 走 arXiv LaTeX 路径（元信息仍用 S2 的正式发表版，venue 显示真实期刊/会议）。查不到 arXiv 版本时才降级 PDF。
- **Pandoc 依赖**：LaTeX→Markdown 转换依赖 `pypandoc-binary`（pip 包，内置 Pandoc 二进制）。若环境未安装，`download_paper.py` 会打印提示并自动降级到 PDF 提取，不会报错中断。

## 多平台聚合搜索（multi 模式）

`--source multi` 会串行查 OpenAlex + Crossref + arXiv（各取 `--limit` 篇），然后 `_merge_results()` 合并去重：

- **去重键优先级**：DOI > arXiv ID（去版本号）> PMID > 标题归一化（小写+去标点）。同一篇被多平台收录时合并为一条，保留信息最完整的记录（按摘要/PDF/DOI 等打分）。
- **排序策略**：①多源命中的论文绝对优先（被多平台收录=更可能是核心文献，会标注“★N源命中”）；②其余按**来源轮转（round-robin）**排序——OA[1]→arXiv[1]→Crossref[1]→OA[2]→...，确保三个平台都有代表进入结果，而非优先级最高的源独占前几名。
- **单源容错**：任一平台失败/限流不影响其他平台，只会跳过该源。
- **limit 语义**：multi 模式下每源各取 limit 篇（输入 3×limit），去重后截到 limit，覆盖面比单源广。

实测 `intent detection`：三源 top20 几乎不重叠（各平台相关性算法不同），轮转排序让 limit=20 的结果里 OpenAlex/arXiv/Crossref 约 7:7:6 均匀分布。

## 扩展方向（当前脚本未实现，如需可以加）

- **Wikidata SPARQL**：结构化学术知识查询。实测做论文搜索覆盖差（schloor.md 的示例查询返回 0 篇），不适合做搜索源。
- **S2 bulk 端点**：`/graph/v1/paper/search/bulk` 支持 token 翻页，适合科研级批量拉取（上千篇）而非交互式搜索。
- 如果要接入新源，遵循现有脚本的模式：写一个 `search_x()` 返回 `_norm_result()` 标准结构即可，run_search/multi 会自动接入。

## 重试与容错（脚本已内置，通常不需要手动处理）

- 两个脚本对 429/500/502/503/504 自动重试 2 次，间隔 1.5s→3s 指数退避；其余 4xx（如 404）不重试，直接报错，避免浪费时间在明显不存在的资源上。
- `search_papers.py` 的 `--source auto`（默认）在 Semantic Scholar **报错或返回空结果**时都会自动降级到 arXiv，不需要用户手动切换 `--source`。
- `download_paper.py` 下载 PDF 后会校验文件头是否为 `%PDF`，付费墙返回的登录页/HTML 会被识别为无效内容并明确报错，不会把错误内容当正文塞进 Markdown。

## 离线测试方法（脚本本身没有测试网络，供本 skill 维护者使用）

两个脚本的 API 地址都做了环境变量覆盖，方便不联网也能做真实的端到端测试，而不只是纯函数级 mock：

```bash
export S2_SEARCH_URL="http://127.0.0.1:<port>/graph/v1/paper/search"
export S2_PAPER_URL="http://127.0.0.1:<port>/graph/v1/paper/{id}"
export ARXIV_API_URL="http://127.0.0.1:<port>/api/query"
export ARXIV_PDF_BASE="http://127.0.0.1:<port>/pdf"
```

搭一个本地 HTTP 服务器返回和真实 API 一致格式的 JSON / Atom XML / PDF 字节，再正常调用两个脚本（走 subprocess，而不是直接 import 内部函数），这样能测到参数解析、环境变量读取、错误退出码等真实脚本行为，而不只是内部函数逻辑。不设置这些环境变量时，两个脚本都会退回默认的真实 API 地址，不影响日常使用。

## 常见报错排查

| 现象 | 原因 | 处理 |
|------|------|------|
| `search_papers.py` 长时间无响应或报错 | Semantic Scholar 限流/网络问题 | 加 `--source arxiv` 直接走兜底 |
| `download_paper.py` 报"未能找到...开放获取 PDF" | 论文没有免费全文（付费墙） | 告知用户无法下载全文,把摘要信息给用户 |
| `download_paper.py` 报"下载到的内容不是有效的 PDF" | 链接返回的是登录页/HTML 而非 PDF | 大概率也是付费墙或链接失效，同上处理 |
| Markdown 正文是空的 | PDF 是扫描件，没有文字层 | 需要 OCR，可参考 `pdf` skill 中的 OCR 章节 |
