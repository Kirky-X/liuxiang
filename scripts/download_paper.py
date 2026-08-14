#!/usr/bin/env python3
"""
download_paper.py — 论文下载并转换为 Markdown（接口二）

输入可以是：
  - arXiv ID              例如 2306.12345、2306.12345v2、hep-th/9901001（旧格式也支持）
  - Semantic Scholar ID   例如 649def34f8be52c8b66281af98ae884c09aef38b
  - DOI                   例如 10.1145/3025453.3025717
  - 直接的 PDF 链接        例如 https://arxiv.org/pdf/2306.12345

转换策略（优先无损格式，PDF 仅作兜底）：
  - arXiv 论文优先下载 LaTeX 源码包，用 Pandoc 转成 Markdown，公式保留为
    标准 $...$ / $$...$$（LaTeX 源码无损，公式、表格、结构最完整）。
  - 当论文只有 PDF（非 arXiv、或 arXiv 作者只提交了 PDF）时，降级用
    pymupdf 提取正文和嵌入图片。PDF 提取无法保留 LaTeX 公式，数学符号会
    丢失或退化成纯文本，属已知局限。
  - 两种路径均会将图片提取到输出 Markdown 同级的 images/ 目录，Markdown
    中以相对路径引用。

OA PDF 解析链：Semantic Scholar openAccessPdf → Unpaywall（DOI 反查 OA 链接）→ arXiv

用法：
    python download_paper.py 2306.12345 -o paper.md
    python download_paper.py 649def34f8be52c8b66281af98ae884c09aef38b -o paper.md
    python download_paper.py https://arxiv.org/pdf/2306.12345 -o paper.md

环境变量（一般不需要设置，测试/自建镜像时可覆盖）：
    S2_PAPER_URL       默认 https://api.semanticscholar.org/graph/v1/paper/{id}
    ARXIV_PDF_BASE     默认 https://arxiv.org/pdf
    ARXIV_EPRINT_URL   默认 https://arxiv.org/e-print/{id}
    ARXIV_API_URL      默认 https://export.arxiv.org/api/query
    UNPAYWALL_API_URL  默认 https://api.unpaywall.org/v2
    UNPAYWALL_EMAIL    Unpaywall 礼貌池邮箱（必须是真实邮箱，example.com 会被拒）
"""

import argparse
import hashlib
import io
import os
import re
import shutil
import sys
import tarfile
import tempfile
import time
import xml.etree.ElementTree as ET  # nosec B405 - 仅用于 findall/findtext，解析已改用 defusedxml

import defusedxml.ElementTree as defused_ET
import requests

S2_PAPER_URL = os.environ.get("S2_PAPER_URL", "https://api.semanticscholar.org/graph/v1/paper/{id}")
S2_FIELDS = "title,authors,year,publicationDate,abstract,externalIds,openAccessPdf,venue"
ARXIV_PDF_BASE = os.environ.get("ARXIV_PDF_BASE", "https://arxiv.org/pdf")
ARXIV_EPRINT_URL = os.environ.get("ARXIV_EPRINT_URL", "https://arxiv.org/e-print/{id}")
# 与 search_papers.py 保持一致，必须用 https 以避免 http→301 重定向的间歇性超时。
ARXIV_API_URL = os.environ.get("ARXIV_API_URL", "https://export.arxiv.org/api/query")
# Unpaywall：DOI → OA PDF 链接解析。需要真实邮箱（example.com 会被拒）。
# 未设置或邮箱无效时自动跳过，不影响其他下载路径。
UNPAYWALL_API_URL = os.environ.get("UNPAYWALL_API_URL", "https://api.unpaywall.org/v2")
UNPAYWALL_EMAIL = os.environ.get("UNPAYWALL_EMAIL", "")

# 新格式：2306.12345 / 2306.12345v2；旧格式（2007年前）：hep-th/9901001、math.GT/0309136
ARXIV_ID_RE = re.compile(
    r"^(arxiv:)?(\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)$",
    re.IGNORECASE,
)
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 1.5

# e-print 端点表示“有 LaTeX 源”的 content-type。application/pdf 表示作者只提交了 PDF。
ARXIV_LATEX_SOURCE_CT = ("application/gzip", "application/x-tar", "application/x-e-print-tar",
                          "application/x-gzip", "application/octet-stream")


def _get_with_retry(url: str, params: dict | None = None, timeout: int = 15):
    last_exc = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout,
                                 headers={"User-Agent": "liuxiang/1.0"})
            if resp.status_code in RETRYABLE_STATUS and attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue
            return resp
        except requests.exceptions.RequestException as e:
            last_exc = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue
    raise last_exc


def slugify(title: str) -> str:
    s = re.sub(r"[^\w\s-]", "", title or "paper", flags=re.UNICODE).strip().lower()
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:80] or "paper"


def fetch_semantic_scholar_meta(s2_identifier: str):
    """按 Semantic Scholar 的 paper id / ArXiv:xxx / DOI:xxx 查询元数据。查不到返回 None。"""
    url = S2_PAPER_URL.format(id=s2_identifier)
    try:
        resp = _get_with_retry(url, params={"fields": S2_FIELDS}, timeout=15)
    except requests.exceptions.RequestException:
        return None
    if resp.status_code != 200:
        return None
    try:
        p = resp.json()
    except ValueError:
        return None
    oa = p.get("openAccessPdf") or {}
    ext = p.get("externalIds") or {}
    return {
        "title": p.get("title"),
        "authors": [a.get("name", "") for a in (p.get("authors") or [])],
        "published": p.get("publicationDate") or (str(p.get("year")) if p.get("year") else None),
        "abstract": p.get("abstract"),
        "venue": p.get("venue"),
        "pdf_url": oa.get("url"),
        # externalIds.ArXiv 让 DOI/S2 标识符也能反查到 arXiv 版本，从而走 LaTeX 无损路径。
        # 多数 CS/AI/物理/数学已发表论文都有 arXiv 预印本，这里拿到的是不带版本号的裸 ID。
        "arxiv_id": ext.get("ArXiv"),
    }


def fetch_arxiv_meta(arxiv_id: str):
    """从 arXiv API Atom feed 补取标题/作者/时间/摘要。

    S2 持续限流（429）是常见现象。此时从 arXiv 自身取元数据（arXiv 不限流、数据权威），
    能避免 Markdown 标题/作者为空。查不到返回 None。
    """
    bare_id = re.sub(r"v\d+$", "", arxiv_id)
    try:
        resp = _get_with_retry(ARXIV_API_URL, params={"id_list": bare_id, "max_results": 1}, timeout=30)
    except requests.exceptions.RequestException:
        return None
    if resp.status_code != 200:
        return None
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    try:
        root = defused_ET.fromstring(resp.text)
    except ET.ParseError:
        return None
    entry = root.find("atom:entry", ns)
    if entry is None:
        return None
    return {
        "title": " ".join((entry.findtext("atom:title", default="", namespaces=ns) or "").split()),
        "authors": [
            (a.findtext("atom:name", default="", namespaces=ns) or "").strip()
            for a in entry.findall("atom:author", ns)
        ],
        "published": entry.findtext("atom:published", default=None, namespaces=ns),
        "abstract": " ".join((entry.findtext("atom:summary", default="", namespaces=ns) or "").split()) or None,
        "venue": "arXiv",
    }


def fetch_unpaywall_pdf(doi: str) -> str | None:
    """通过 Unpaywall 按 DOI 查找 OA PDF 链接。返回最佳 OA URL，找不到或邮箱无效返回 None。

    Unpaywall 覆盖 1.2 亿+ DOI，常能找到 S2 遗漏的机构仓库版本。
    需要真实邮箱（example.com 会被拒），未设置 UNPAYWALL_EMAIL 时直接跳过。
    """
    if not UNPAYWALL_EMAIL:
        return None
    url = f"{UNPAYWALL_API_URL}/{doi}"
    try:
        resp = _get_with_retry(url, params={"email": UNPAYWALL_EMAIL}, timeout=15)
    except requests.exceptions.RequestException:
        return None
    if resp.status_code != 200:
        return None
    try:
        data = resp.json()
    except ValueError:
        return None
    if not data.get("is_oa"):
        return None
    # 优先用 best_oa_location（Unpaywall 已排序）
    best = data.get("best_oa_location") or {}
    if best.get("url"):
        return best["url"]
    # 兑底：遍历所有 oa_locations 找第一个有 URL 的
    for loc in (data.get("oa_locations") or []):
        if loc.get("url"):
            return loc["url"]
    return None


def resolve_metadata(identifier: str):
    """返回 (meta_dict, pdf_url, arxiv_id)。

    arxiv_id 是「可走 LaTeX 无损路径的 arXiv 版本 ID」：用户直接给 arXiv ID 时就是它本身；
    给 DOI/S2 ID 时，若该论文有 arXiv 预印本则从 Semantic Scholar 的 externalIds 反查到（可能为 None）。
    找不到开放获取 PDF 时抛 RuntimeError。
    """
    identifier = identifier.strip()

    # 情况一：直接给的 URL——无法推断 arXiv 版本，只能走 PDF。
    if identifier.startswith(("http://", "https://")):
        meta = {"title": None, "authors": [], "published": None, "abstract": None, "venue": None}
        return meta, identifier, None

    # 情况二：arXiv ID —— PDF 链接直接拼接，不依赖 Semantic Scholar 是否收录，
    # 这样即使 S2 查不到元数据（比如刚提交的新论文，或 S2 限流），下载依然能成功。
    m = ARXIV_ID_RE.match(identifier)
    if m:
        arxiv_id = m.group(2)
        bare_id = re.sub(r"v\d+$", "", arxiv_id)  # S2 的 ArXiv 外部 ID 一般不带版本号
        meta = fetch_semantic_scholar_meta(f"ArXiv:{bare_id}")
        if not meta:  # S2 限流/未收录时，从 arXiv API 补取元数据
            meta = fetch_arxiv_meta(arxiv_id) or {
                "title": None, "authors": [], "published": None, "abstract": None, "venue": None,
            }
        meta.setdefault("venue", None)
        if not meta.get("venue"):
            meta["venue"] = "arXiv"
        pdf_url = f"{ARXIV_PDF_BASE}/{arxiv_id}"
        return meta, pdf_url, arxiv_id

    # 情况三：DOI
    if DOI_RE.match(identifier):
        meta = fetch_semantic_scholar_meta(f"DOI:{identifier}")
        if not meta:
            raise RuntimeError(f"未能找到 DOI {identifier} 对应的论文（Semantic Scholar 暂未收录）。")
        if not meta.get("pdf_url") and not meta.get("arxiv_id"):
            # S2 没有 OA PDF 也没有 arXiv 版本，尝试 Unpaywall 按 DOI 反查
            up_pdf = fetch_unpaywall_pdf(identifier)
            if up_pdf:
                meta["pdf_url"] = up_pdf
            else:
                raise RuntimeError(f"未能找到 DOI {identifier} 对应的开放获取 PDF（该论文可能没有免费全文）。")
        # 优先用正式发表版信息（venue 为真实期刊/会议），PDF 兑底（无 arXiv 版本时必需）。
        pdf_url = meta.get("pdf_url") or f"{ARXIV_PDF_BASE}/{meta['arxiv_id']}"
        return meta, pdf_url, meta.get("arxiv_id")

    # 情况四：当作 Semantic Scholar 的 paper ID
    meta = fetch_semantic_scholar_meta(identifier)
    if not meta:
        raise RuntimeError(f"未能找到标识符 {identifier} 对应的论文（Semantic Scholar 暂未收录，或标识符有误）。")
    if not meta.get("pdf_url") and not meta.get("arxiv_id"):
        # S2 ID 无法反查 DOI，Unpaywall 需要 DOI，此处无法使用
        raise RuntimeError(f"未能找到标识符 {identifier} 对应的开放获取 PDF（该论文可能没有免费全文，仅摘要可用，或标识符有误）。")
    pdf_url = meta.get("pdf_url") or f"{ARXIV_PDF_BASE}/{meta['arxiv_id']}"
    return meta, pdf_url, meta.get("arxiv_id")


def download_pdf(pdf_url: str) -> str:
    resp = _get_with_retry(pdf_url, timeout=60)
    resp.raise_for_status()
    if not resp.content.startswith(b"%PDF"):
        raise RuntimeError(f"下载到的内容不是有效的 PDF 文件（来自 {pdf_url}）。链接可能需要登录/付费访问，或已失效。")
    fd = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    fd.write(resp.content)
    fd.close()
    return fd.name


def pdf_to_markdown_body(pdf_path: str, images_dir: str | None = None) -> str:
    """PDF 兜底提取（有损）。无法保留 LaTeX 公式，数学符号会退化成纯文本。

    使用 pymupdf 同时提取嵌入图片（保存到 images_dir），在 Markdown 中以
    相对路径引用。属于降级路径：仅当论文没有 LaTeX 源码时使用。
    """
    import pymupdf  # pymupdf (fitz)

    parts = []
    page_image_refs = {}  # page_num -> [(filename, alt_text)]

    if images_dir:
        os.makedirs(images_dir, exist_ok=True)
        seen_hashes = set()

    with pymupdf.open(pdf_path) as doc:
        for page_idx, page in enumerate(doc, 1):
            text = (page.get_text() or "").strip()

            # 提取本页嵌入的图片
            if images_dir:
                img_list = page.get_images(full=True)
                for img_idx, img_info in enumerate(img_list):
                    xref = img_info[0]
                    try:
                        base_image = doc.extract_image(xref)
                        if not base_image:
                            continue
                        image_bytes = base_image["image"]

                        # 跳过小图标（< 5KB 通常是装饰性图标）
                        if len(image_bytes) < 5000:
                            continue

                        # 去重：相同内容的图片只保存一次
                        img_hash = hashlib.md5(image_bytes, usedforsecurity=False).hexdigest()[:12]
                        if img_hash in seen_hashes:
                            continue
                        seen_hashes.add(img_hash)

                        ext = base_image.get("ext", "png")
                        filename = f"page{page_idx}_img{img_idx + 1}.{ext}"
                        filepath = os.path.join(images_dir, filename)
                        with open(filepath, "wb") as img_f:
                            img_f.write(image_bytes)

                        page_image_refs.setdefault(page_idx, []).append(
                            (filename, "figure")
                        )
                    except Exception:  # nosec B112 - 单张图片提取失败不影响整体流程
                        continue

            parts.append(f"<!-- page {page_idx} -->\n\n{text}")

            # 在该页文字后插入图片引用
            if page_idx in page_image_refs:
                for fname, alt in page_image_refs[page_idx]:
                    parts.append(f"\n![{alt}](images/{fname})\n")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# LaTeX 源 → Markdown（无损，优先路径）
# ---------------------------------------------------------------------------

def _find_main_tex(src_dir: str) -> str | None:
    """在解压目录里找到包含 \\documentclass 的主 .tex 文件。"""
    candidates = []
    for root, _dirs, files in os.walk(src_dir):
        for fn in files:
            if fn.endswith(".tex"):
                candidates.append(os.path.join(root, fn))
    if not candidates:
        return None
    # 优先文件名为 main.tex / paper.tex 的
    for pref in ("main.tex", "paper.tex", "ms.tex", "article.tex"):
        for c in candidates:
            if os.path.basename(c).lower() == pref:
                return c
    # 否则找含 \documentclass 的
    for c in candidates:
        try:
            with open(c, encoding="utf-8", errors="ignore") as f:
                head = f.read(8192)
            if "\\documentclass" in head:
                return c
        except OSError:
            continue
    return candidates[0]


def _expand_inputs(src_dir: str, main_tex_path: str) -> str:
    """读取主 .tex 并递归展开 \\input{} / \\include{}，返回合并后的完整 LaTeX 文本。"""
    seen = set()

    def read_with_inputs(path: str) -> str:
        real = os.path.realpath(path)
        if real in seen:
            return ""
        seen.add(real)
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            return ""

        def repl(m):
            target = m.group(1).strip()
            if not target.endswith(".tex"):
                target += ".tex"
            sub = os.path.join(os.path.dirname(path), target)
            if os.path.isfile(sub):
                return "\n" + read_with_inputs(sub) + "\n"
            return ""

        return re.sub(r"\\(?:input|include)\{([^}]+)\}", repl, content)

    return read_with_inputs(main_tex_path)


def _normalize_pandoc_math(md: str) -> str:
    """规范化 Pandoc GFM 输出的公式定界符。

    Pandoc 把 LaTeX 公式输出成两种 GFM 特有形态，需转成标准 Markdown 数学语法：
    - 行内公式 `` $`...`$ ``  →  $...$
    - 块级公式 `` ```math \\n \\begin{equation}...\\end{equation} \\n ``` ``  →  $$...$$
    另外清理公式编号标签 \\label{} 和交叉引用，避免渲染出乱码。
    """
    # 行内公式: $`...`$ -> $...$（`[^`\\]` 与 `\\.` 互斥，避免 ReDoS）
    md = re.sub(r"\$`((?:[^`\\]|\\.)*)`\$", lambda m: "$" + m.group(1) + "$", md)

    # 块级公式: pandoc 输出成 ```math (或 ```latex / 空) 围栏，内含 \begin{equation}/eqnarray/align...
    def block_repl(m):
        inner = m.group(1)
        inner = re.sub(r"\\label\{[^}]*\}", "", inner)
        inner = re.sub(r"\\(?:begin|end)\{(?:equation|eqnarray|align\*?|gather\*?|multline\*?|cases|split)\}", "", inner)
        inner = re.sub(r"\n{3,}", "\n\n", inner.strip())
        return "$$\n" + inner + "\n$$"

    block_pattern = (
        r"```[ ]*(?:math|latex|tex)?[ ]*\n"
        r"(\\begin\{(?:equation|eqnarray|align\*?|gather\*?|multline\*?|cases)\}"
        r".*?\\end\{(?:equation|eqnarray|align\*?|gather\*?|multline\*?|cases)\})"
        r"\s*\n```"
    )
    md = re.sub(block_pattern, block_repl, md, flags=re.DOTALL)

    # 兜底：清理游离的 \label{}（如行内残留的公式编号）
    md = re.sub(r"\\label\{[^}]*\}", "", md)
    return md


def _strip_html_tags(text: str) -> str:
    """移除 HTML 标签，保留纯文本内容。"""
    return re.sub(r'<[^>]+>', '', text).strip()


def _convert_pdf_to_png(pdf_path: str, png_path: str) -> bool:
    """用 pymupdf 将 PDF 第一页渲染为 PNG 图片。成功返回 True。"""
    try:
        import pymupdf
        doc = pymupdf.open(pdf_path)
        page = doc[0]
        # 使用 2x 缩放率保证清晰度
        mat = pymupdf.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)
        pix.save(png_path)
        doc.close()
        return True
    except Exception:
        return False


def _strip_latex_div_noise(md: str) -> str:
    """清理 Pandoc 把 LaTeX 环境（\begin{table*}/center/minipage/CCSXML...）转成的多余 div 标签。

    Pandoc 会把 LaTeX 环境原样输出成 HTML div 标签（`<div class="环境名">` 或 `<div id="tab:xxx">` 错点），其中：
    - CCSXML：ACM 分类元数据 XML（<ccs2012>...），是机器可读的元数据，对阅读无意义，整块删除。
    - 其余（center/table*/minipage/algorithm/acks/表格错点 id...）：保留内部内容（图片、表格、正文、
      算法步骤），只移除包裹的 div 标签——这些环境在 Markdown 里没有对等表达，裸内容反而更可读。
    """
    # CCSXML 整块删除（含被 Pandoc 转义的 XML 内容）
    md = re.sub(r'<div class="CCSXML">.*?</div>', '', md, flags=re.DOTALL)
    # 其余 div 标签：移除开/闭标签（无论 class、id 还是其他属性），保留内部内容
    md = re.sub(r'<div[^>]*>\s*\n?', '', md)
    md = re.sub(r'\n?</div>', '\n', md)
    # 将 pandoc 产生的 HTML 图片标签转换为 Markdown 图片语法。
    # 1) <img src="..." ... alt="..." /> → ![alt](src)
    md = re.sub(
        r'<img\s+[^>]*src="([^"]+)"[^>]*/?>',
        lambda m: f'![figure]({m.group(1)})',
        md,
    )
    # 2) <embed src="..." ... /> → ![figure](src)
    md = re.sub(
        r'<embed\s+[^>]*src="([^"]+)"[^>]*/?>',
        lambda m: f'![figure]({m.group(1)})',
        md,
    )
    # 3) 将 pandoc 图片占位 span 转换为 Markdown 图片语法（备用）。
    md = re.sub(
        r'<span\s+class="image\s+placeholder"[^>]*(?:data-)?original-image-src="([^"]+)"[^>]*>.*?</span>',
        r'![figure](\1)',
        md,
    )
    # 4) 移除 <figure> 包裹标签（保留内部内容），将 <figcaption> 转为斜体注释。
    #    很多 Markdown 渲染器不支持 <figure>，裸内容反而更可读。
    md = re.sub(r'<figure[^>]*>\s*\n?', '', md)
    md = re.sub(r'\n?</figure>', '\n', md)
    md = re.sub(
        r'<figcaption[^>]*>(.*?)</figcaption>',
        lambda m: f'\n*{_strip_html_tags(m.group(1))}*\n',
        md,
        flags=re.DOTALL,
    )
    # 清理删除/去标签后产生的连续空行（压成最多两个换行，即一个空行）
    md = re.sub(r'\n{3,}', '\n\n', md)
    return md


def latex_source_to_markdown(arxiv_id: str, images_dir: str | None = None) -> str | None:
    """下载 arXiv LaTeX 源码包并用 Pandoc 转成 Markdown（公式无损）。

    任何一步失败都返回 None，由调用方降级到 PDF 提取。这是有意为之：
    LaTeX 源是「尽力优化」而非「必需」，失败不应阻断下载流程。
    """
    try:
        import pypandoc
        # 触发内置 pandoc 二进制定位；若未安装会在下面抛异常
        pypandoc.get_pandoc_version()
    except (ImportError, OSError) as e:
        print(f"[提示] Pandoc 不可用（{e}），将降级到 PDF 提取（公式无法保留）。", file=sys.stderr)
        return None

    eprint_url = ARXIV_EPRINT_URL.format(id=re.sub(r"v\d+$", "", arxiv_id))
    try:
        resp = _get_with_retry(eprint_url, timeout=60)
    except requests.exceptions.RequestException as e:
        print(f"[提示] 下载 LaTeX 源失败（{e}），降级到 PDF。", file=sys.stderr)
        return None
    if resp.status_code != 200:
        print(f"[提示] LaTeX 源端点返回 {resp.status_code}（可能只有 PDF），降级到 PDF 提取。", file=sys.stderr)
        return None

    content_type = resp.headers.get("Content-Type", "")
    # application/pdf 表示作者只提交了 PDF，没有 LaTeX 源
    if "pdf" in content_type.lower():
        print("[提示] 该论文仅有 PDF（作者未提交 LaTeX 源），降级到 PDF 提取。", file=sys.stderr)
        return None

    # 解压源码包（gzip → tar）
    tmp_dir = tempfile.mkdtemp(prefix="arxiv_src_")
    _image_files = []  # 将在解压后填充
    try:
        try:
            tar = tarfile.open(fileobj=io.BytesIO(resp.content), mode="r:*")
        except tarfile.TarError:
            # 单个 .tex.gz 文件（非 tar 包）
            if resp.content[:2] == b"\x1f\x8b":
                import gzip
                single = gzip.decompress(resp.content).decode("utf-8", errors="ignore")
                with open(os.path.join(tmp_dir, "single.tex"), "w", encoding="utf-8") as f:
                    f.write(single)
                tar = None
            else:
                print("[提示] 源码包格式无法识别，降级到 PDF。", file=sys.stderr)
                return None
        if tar:
            # 过滤掉不安全的路径（防止路径穿越）
            for member in tar.getmembers():
                if member.name.startswith("/") or ".." in member.name.split("/"):
                    continue
                try:
                    tar.extract(member, tmp_dir)
                except (tarfile.TarError, OSError):
                    pass
            tar.close()

        # 收集 tarball 中所有图片文件的路径（相对于 tmp_dir），
        # 供 pandoc 转换后手动复制到输出 images/ 目录。
        _IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".pdf", ".eps", ".gif", ".bmp", ".svg"}
        _image_files = []  # [(relative_path, absolute_path)]
        for root, _dirs, files in os.walk(tmp_dir):
            for fn in files:
                if os.path.splitext(fn)[1].lower() in _IMAGE_EXTS:
                    abs_path = os.path.join(root, fn)
                    rel_path = os.path.relpath(abs_path, tmp_dir)
                    _image_files.append((rel_path, abs_path))

    except Exception as e:
        print(f"[提示] 解压源码包失败（{e}），降级到 PDF。", file=sys.stderr)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        if images_dir:
            shutil.rmtree(images_dir, ignore_errors=True)
        return None

    try:
        main_tex = _find_main_tex(tmp_dir)
        if not main_tex:
            print("[提示] 源码包中未找到 .tex 文件，降级到 PDF。", file=sys.stderr)
            return None
        full_latex = _expand_inputs(tmp_dir, main_tex)

        # 写入临时 .tex 供 pandoc 读取（pandoc 需要文件路径来解析相对引用）
        merged_tex = os.path.join(tmp_dir, "_merged.tex")
        with open(merged_tex, "w", encoding="utf-8") as f:
            f.write(full_latex)

        # 构建 pandoc 参数
        extra_args = ["--wrap=none"]

        markdown = pypandoc.convert_file(
            merged_tex, "gfm", format="latex",
            extra_args=extra_args,
        )
        markdown = _normalize_pandoc_math(markdown)
        # 注意：图片复制和恢复逻辑必须在 _strip_latex_div_noise 之前运行，
        # 因为恢复代码需要 <figure id="..."> 标签来定位插入点。

        if not markdown.strip():
            print("[提示] Pandoc 转换结果为空，降级到 PDF。", file=sys.stderr)
            return None

        # pandoc 转换成功后，手动将 tarball 中的图片复制到输出 images/ 目录。
        # pandoc 在 LaTeX→Markdown 时无法自动提取图片文件，但会在 Markdown 中
        # 保留 \includegraphics 的引用路径，手动复制后引用即可生效。
        # PDF 格式的图片（矢量图）用 pymupdf 渲染为 PNG，因为多数 Markdown
        # 渲染器不支持 PDF 作为图片格式。
        if images_dir and _image_files:
            os.makedirs(images_dir, exist_ok=True)
            copied = 0
            pdf_to_png_map = {}  # {原始 basename.pdf: 新 basename.png}
            for rel_path, abs_path in _image_files:
                basename = os.path.basename(rel_path)
                if basename.lower().endswith(".pdf") or basename.lower().endswith(".eps"):
                    # PDF/EPS 图片：渲染为 PNG
                    png_name = os.path.splitext(basename)[0] + ".png"
                    dst = os.path.join(images_dir, png_name)
                    if _convert_pdf_to_png(abs_path, dst):
                        pdf_to_png_map[basename] = png_name
                        copied += 1
                    else:
                        # 渲染失败，直接复制原文件
                        fallback = os.path.join(images_dir, basename)
                        try:
                            shutil.copy2(abs_path, fallback)
                            copied += 1
                        except OSError:
                            pass
                else:
                    dst = os.path.join(images_dir, basename)
                    try:
                        shutil.copy2(abs_path, dst)
                        copied += 1
                    except OSError:
                        pass
            # 更新 markdown 中的 PDF/EPS 引用为 PNG
            for old_name, new_name in pdf_to_png_map.items():
                markdown = markdown.replace(old_name, new_name)

            # 恢复被 pandoc 丢失的图片引用：
            # 找出已复制但在 markdown 中未被引用的图片，
            # 从 LaTeX 源中找到它们所在的 figure 环境的 caption 关键字，
            # 在 markdown 中搜索匹配的位置插入图片。
            _img_basenames = {os.path.basename(rp) for rp, _ in _image_files}
            _final_basenames = set()
            for bn in _img_basenames:
                _final_basenames.add(pdf_to_png_map.get(bn, bn))
            # 找出已复制但在 markdown 中未被引用的图片
            # 注意：此时 markdown 仍包含 HTML <img>/<embed> 标签，
            # 需要同时检查 Markdown 和 HTML 格式的引用。
            _referenced = set()
            for m in re.finditer(r'!\[[^\]]*\]\(([^)]+)\)', markdown):
                _referenced.add(os.path.basename(m.group(1)))
            for m in re.finditer(r'<(?:img|embed)[^>]*src="([^"]+)"', markdown):
                _referenced.add(os.path.basename(m.group(1)))
            _missing = _final_basenames - _referenced

            if _missing and full_latex:
                # 从 LaTeX 中提取每个 figure/figure* 环境的 image + caption 关键字
                for fig_block in re.finditer(
                    r'\\begin\{figure\*?\}([^\n]*)\n(.*?)\n\s*\\end\{figure\*?\}',
                    full_latex, re.DOTALL,
                ):
                    block_content = fig_block.group(2)
                    # 提取图片文件名
                    img_match = re.search(r'\\includegraphics[^{]*\{([^}]+)\}', block_content)
                    if not img_match:
                        continue
                    img_name = os.path.basename(img_match.group(1))
                    img_name = pdf_to_png_map.get(img_name, img_name)
                    if img_name not in _missing:
                        continue
                    # 提取 caption 中的关键字
                    cap_match = re.search(r'\\caption\{(.+?)(?:\n\s*\\label|\n\s*\\end\{figure)', block_content, re.DOTALL)
                    if not cap_match:
                        continue
                    cap_text = cap_match.group(1).strip()[:80]
                    # 去掉 LaTeX 命令（包括嵌套花括号），保留纯文字
                    cap_text = re.sub(r'\\(?:small|tiny|footnotesize|scriptsize|large|Large|LARGE|huge|Huge|centering)\b', '', cap_text)
                    cap_text = re.sub(r'\\[a-zA-Z]+\{', ' ', cap_text)
                    cap_text = re.sub(r'[{}]', ' ', cap_text)
                    cap_text = re.sub(r'\\[^a-zA-Z]', ' ', cap_text)
                    cap_text = re.sub(r'[^\w\s]', ' ', cap_text).strip()
                    # 取前 3 个有意义的词作为搜索关键字（跳过长度 <=2 的词）
                    words = [w for w in cap_text.split() if len(w) > 2][:3]
                    if not words:
                        continue
                    search_key = ' '.join(words)
                    # 在 markdown 中搜索包含这些关键字的位置
                    md_pos = markdown.lower().find(search_key.lower())
                    if md_pos >= 0:
                        # 在该位置前插入图片引用
                        line_start = markdown.rfind('\n', 0, md_pos) + 1
                        markdown = (
                            markdown[:line_start]
                            + f'![figure](images/{img_name})\n\n'
                            + markdown[line_start:]
                        )
                        _missing.discard(img_name)
                        continue  # 继续处理下一个缺失的图片

            if copied:
                print(f"[提示] 已提取 {copied} 个图片文件到 {images_dir}（PDF 矢量图已转为 PNG）", file=sys.stderr)

        # 清理 HTML 标签噪音（必须在图片恢复之后运行）
        markdown = _strip_latex_div_noise(markdown)

        return markdown
    except Exception as e:
        print(f"[提示] Pandoc 转换 LaTeX 失败（{e}），降级到 PDF。", file=sys.stderr)
        return None
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def build_markdown(meta: dict, body: str, source_ref: str, conversion: str = "pdf") -> str:
    title = meta.get("title") or "（未知标题）"
    authors = ", ".join(a for a in (meta.get("authors") or []) if a) or "未知"
    published = meta.get("published") or "未知"
    venue = meta.get("venue") or ""
    abstract = (meta.get("abstract") or "").strip()

    lines = [f"# {title}", ""]
    lines.append(f"- **作者**: {authors}")
    lines.append(f"- **发表时间**: {published}")
    if venue:
        lines.append(f"- **来源/期刊**: {venue}")
    lines.append(f"- **来源标识**: {source_ref}")
    # 明确标注转换方式，让用户知道公式是否完整保留
    if conversion == "latex":
        lines.append("- **转换方式**: LaTeX 源码 → Markdown（公式、结构完整保留）")
    else:
        lines.append("- **转换方式**: PDF 文本提取（公式可能退化，如有数学符号异常请见谅）")
    lines.append("")
    if abstract:
        lines.append("## 摘要")
        lines.append("")
        lines.append(abstract)
        lines.append("")
    lines.append("## 正文")
    lines.append("")
    lines.append(body if body else "*（未能提取到正文文字，可能是扫描版 PDF，需要 OCR。）*")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="下载论文并转换为 Markdown")
    ap.add_argument("identifier", help="arXiv ID / Semantic Scholar ID / DOI / 直接 PDF 链接")
    ap.add_argument("-o", "--output", default=None, help="输出的 .md 文件路径，默认根据标题自动生成")
    args = ap.parse_args()

    try:
        meta, pdf_url, arxiv_id = resolve_metadata(args.identifier)
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    # 优先尝试 arXiv LaTeX 源（无损，公式完整）；无论用户给的是 arXiv ID、DOI 还是 S2 ID，
    # 只要反查到 arXiv 版本就走 LaTeX 路径。反查不到或无源码时降级 PDF。
    output_path = args.output or f"{slugify(meta.get('title'))}.md"
    images_dir = os.path.join(os.path.dirname(os.path.abspath(output_path)), "images")

    body = None
    conversion = "pdf"
    if arxiv_id:
        print("正在下载 LaTeX 源码并转换（公式无损）...", file=sys.stderr)
        body = latex_source_to_markdown(arxiv_id, images_dir=images_dir)
        if body is not None:
            conversion = "latex"

    if body is None:
        print(f"正在下载 PDF: {pdf_url}", file=sys.stderr)
        try:
            pdf_path = download_pdf(pdf_url)
        except Exception as e:
            print(f"错误: 下载/校验 PDF 失败 — {e}", file=sys.stderr)
            sys.exit(1)

        print("正在提取正文并转换为 Markdown...", file=sys.stderr)
        try:
            body = pdf_to_markdown_body(pdf_path, images_dir=images_dir)
        except Exception as e:
            print(f"错误: PDF 解析失败 — {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            try:
                os.unlink(pdf_path)
            except OSError:
                pass

    markdown = build_markdown(meta, body, args.identifier, conversion)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"已保存: {output_path}")


if __name__ == "__main__":
    main()
