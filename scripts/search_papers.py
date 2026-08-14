#!/usr/bin/env python3
"""
search_papers.py — 学术论文搜索（接口一）

按主题关键词或论文标题搜索学术论文，返回标题、作者、发表时间、摘要等信息。

主搜索源：Semantic Scholar（覆盖期刊+预印本，免费，无需 API Key）
兜底搜索源：arXiv（当 Semantic Scholar 请求失败/超限/无结果时自动切换，仅覆盖预印本）

用法：
    python search_papers.py "quantum computing" --limit 10
    python search_papers.py "Attention Is All You Need" --mode title
    python search_papers.py "large language model" --source arxiv --limit 5
    python search_papers.py "generative ai" --json > results.json

环境变量（一般不需要设置，测试/自建镜像时可覆盖）：
    S2_SEARCH_URL   默认 https://api.semanticscholar.org/graph/v1/paper/search
    ARXIV_API_URL   默认 http://export.arxiv.org/api/query
"""

import argparse
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET

import requests

S2_SEARCH_URL = os.environ.get("S2_SEARCH_URL", "https://api.semanticscholar.org/graph/v1/paper/search")
S2_FIELDS = "title,authors,year,publicationDate,abstract,externalIds,openAccessPdf,venue,url"
# 注意：必须用 https。arXiv 会把 http://export.arxiv.org 301 重定向到 https，
# 而 requests 跟随该重定向时常出现间歇性读超时，直接用 https 可省去这次往返。
ARXIV_API_URL = os.environ.get("ARXIV_API_URL", "https://export.arxiv.org/api/query")
# 以下三个平台均免费、无需 API Key（OpenAlex 2026.2 起需 Key，届时加 OPENALEX_EMAIL 环境变量进礼貌池即可）。
OPENALEX_API_URL = os.environ.get("OPENALEX_API_URL", "https://api.openalex.org/works")
CROSSREF_API_URL = os.environ.get("CROSSREF_API_URL", "https://api.crossref.org/works")
PUBMED_ESEARCH_URL = os.environ.get("PUBMED_ESEARCH_URL", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi")
PUBMED_ESUMMARY_URL = os.environ.get("PUBMED_ESUMMARY_URL", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi")
# Crossref/OpenAlex 鼓励带联系邮箱进入“礼貌用户池”（更高速率限制），不强制但推荐。
CONTACT_EMAIL = os.environ.get("LIUXIANG_EMAIL", "liuxiang@example.com")

# 瞬时错误（限流/网络抖动）重试次数与间隔。429/5xx 才重试，4xx（除429）直接放弃。
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 1.5


def _get_with_retry(url: str, params: dict, timeout: int = 15) -> requests.Response:
    last_exc = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout,
                                 headers={"User-Agent": "liuxiang/1.0"})
            if resp.status_code in RETRYABLE_STATUS and attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            last_exc = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue
    raise last_exc


def _norm_result(title=None, authors=None, published=None, abstract=None,
                 venue=None, semantic_scholar_id=None, doi=None, arxiv_id=None,
                 pmid=None, pdf_url=None, page_url=None, source=None):
    """把各平台异构的字段统一成本技能的标准结果结构。

    所有 search_xxx() 都走这个出口，保证下游 format_human/下载接口拿到的字段一致。
    标识符字段（doi/arxiv_id/pmid/semantic_scholar_id）按实际有无填充，下载时按优先级反查。
    """
    return {
        "title": title,
        "authors": authors or [],
        "published": published,
        "abstract": abstract,
        "venue": venue,
        "semantic_scholar_id": semantic_scholar_id,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "pmid": pmid,
        "pdf_url": pdf_url,
        "page_url": page_url,
        "source": source,
    }


def search_semantic_scholar(query: str, limit: int, mode: str):
    # mode 目前对 Semantic Scholar 无影响：其 /search 端点本身就是自由文本匹配，
    # 标题搜索直接把标题当 query 传即可，不需要额外的字段前缀。
    params = {
        "query": query,
        "fields": S2_FIELDS,
        "limit": limit,
    }
    resp = _get_with_retry(S2_SEARCH_URL, params, timeout=15)
    try:
        data = resp.json()
    except ValueError as e:
        raise RuntimeError(f"Semantic Scholar 返回了无法解析的内容: {e}")

    results = []
    for p in data.get("data", []) or []:
        authors = [a.get("name", "") for a in (p.get("authors") or [])]
        ext = p.get("externalIds") or {}
        oa = p.get("openAccessPdf") or {}
        results.append(_norm_result(
            title=p.get("title"),
            authors=authors,
            published=p.get("publicationDate") or (str(p.get("year")) if p.get("year") else None),
            abstract=p.get("abstract"),
            venue=p.get("venue"),
            semantic_scholar_id=p.get("paperId"),
            doi=ext.get("DOI"),
            arxiv_id=ext.get("ArXiv"),
            pdf_url=oa.get("url"),
            page_url=p.get("url"),
            source="semantic_scholar",
        ))
    return results


def search_arxiv(query: str, limit: int, mode: str):
    prefix = "ti" if mode == "title" else "all"
    clean = query.replace('"', "").strip()
    terms = clean.split()
    if mode == "title":
        # title 模式要精确匹配完整标题，用短语查询；arXiv 短语查询要求词序一致，
        # 这正是标题精确查找所需要的（和 topic 模式相反）。
        q = f'{prefix}:"{clean}"' if clean else f'{prefix}:"{query}"'
    elif len(terms) <= 1:
        q = f'{prefix}:{terms[0]}' if terms else f'{prefix}:"{query}"'
    else:
        # topic 模式：多词查询用 AND 拆词。arXiv 的短语查询 "..." 要求词序完全一致，
        # 多词主题查询几乎必然 0 命中，拆成 AND 连接的单字段查询能兼顾召回率与相关性。
        q = " AND ".join(f'{prefix}:{t}' for t in terms)
    params = {
        "search_query": q,
        "start": 0,
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    # arXiv 端点（经 https 重定向后）间歇性慢响应，用比 S2 更宽松的超时。
    resp = _get_with_retry(ARXIV_API_URL, params, timeout=30)
    raw = resp.text

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(raw)

    results = []
    for entry in root.findall("atom:entry", ns):
        entry_id = entry.findtext("atom:id", default="", namespaces=ns)
        arxiv_id = entry_id.rsplit("/abs/", 1)[-1] if "/abs/" in entry_id else entry_id
        title = " ".join((entry.findtext("atom:title", default="", namespaces=ns) or "").split())
        summary = " ".join((entry.findtext("atom:summary", default="", namespaces=ns) or "").split())
        published = entry.findtext("atom:published", default="", namespaces=ns)
        authors = [
            (a.findtext("atom:name", default="", namespaces=ns) or "").strip()
            for a in entry.findall("atom:author", ns)
        ]
        pdf_url = None
        for link in entry.findall("atom:link", ns):
            if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                pdf_url = link.attrib.get("href")
        results.append(_norm_result(
            title=title,
            authors=authors,
            published=published,
            abstract=summary,
            venue="arXiv",
            arxiv_id=arxiv_id,
            pdf_url=pdf_url or f"https://arxiv.org/pdf/{arxiv_id}",
            page_url=entry_id,
            source="arxiv",
        ))
    return results


def search_openalex(query: str, limit: int, mode: str):
    """OpenAlex /works 搜索。免费无 Key，覆盖面最广的开放学术图谱。

    优势：返回 open_access.oa_url（开放获取 PDF），且 best_oa_location 常含 DOI，
    与下载接口衔接最好——拿到的 DOI 能直接走下载 + arXiv 反查 LaTeX 路径。
    2026.2 起需 API Key，目前免费；带 mailto 进礼貌池以享更高速率限制。
    """
    params = {
        "search": query,
        "per_page": min(limit, 200),
        "mailto": CONTACT_EMAIL,
        "select": "id,display_name,authorships,publication_date,abstract_inverted_index,doi,primary_location,open_access",
    }
    resp = _get_with_retry(OPENALEX_API_URL, params, timeout=20)
    try:
        data = resp.json()
    except ValueError as e:
        raise RuntimeError(f"OpenAlex 返回了无法解析的内容: {e}")

    results = []
    for w in data.get("results", []) or []:
        # 摘要是倒排索引格式，需还原成文本
        idx = w.get("abstract_inverted_index") or {}
        if idx:
            positions = []
            for term, locs in idx.items():
                for pos in locs:
                    positions.append((pos, term))
            abstract = " ".join(t for _, t in sorted(positions))
        else:
            abstract = None
        authors = [a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or [])]
        doi = (w.get("doi") or "").replace("https://doi.org/", "") or None
        oa = w.get("open_access") or {}
        pdf_url = oa.get("oa_url")
        loc = w.get("primary_location") or {}
        venue = (loc.get("source") or {}).get("display_name") if loc else None
        results.append(_norm_result(
            title=w.get("display_name"),
            authors=authors,
            published=w.get("publication_date"),
            abstract=abstract,
            venue=venue,
            doi=doi,
            pdf_url=pdf_url,
            page_url=w.get("id"),
            source="openalex",
        ))
    return results


def search_crossref(query: str, limit: int, mode: str):
    """Crossref /works 搜索。免费无 Key，DOI 注册机构，元数据最规范。

    覆盖所有正式发表论文（期刊/会议/书籍）。不含预印本摘要质量较低，但 DOI 最权威——
    拿到的 DOI 走下载接口时能反查 arXiv 走 LaTeX 路径。带 mailto 进礼貌池。
    """
    params = {
        "query.bibliographic": query,
        "rows": min(limit, 100),
        "mailto": CONTACT_EMAIL,
        "select": "DOI,title,author,published,container-title,abstract,URL",
    }
    resp = _get_with_retry(CROSSREF_API_URL, params, timeout=20)
    try:
        data = resp.json()
    except ValueError as e:
        raise RuntimeError(f"Crossref 返回了无法解析的内容: {e}")

    results = []
    for item in data.get("message", {}).get("items", []) or []:
        titles = item.get("title") or []
        title = titles[0] if titles else None
        authors = []
        for a in item.get("author") or []:
            name = (a.get("family") or "") + ((" " + a.get("given")) if a.get("given") else "")
            authors.append(name.strip())
        pub = item.get("published") or item.get("published-print") or item.get("published-online") or {}
        parts = pub.get("date-parts") or [[]]
        published = "-".join(str(p) for p in parts[0]) if parts and parts[0] else None
        containers = item.get("container-title") or []
        venue = containers[0] if containers else None
        # Crossref 摘要常含 JATS XML 标签，去标签纯净化
        abstract = item.get("abstract")
        if abstract:
            abstract = re.sub(r"<[^>]+>", "", abstract).strip()
        results.append(_norm_result(
            title=title,
            authors=authors,
            published=published,
            abstract=abstract,
            venue=venue,
            doi=item.get("DOI"),
            page_url=item.get("URL"),
            source="crossref",
        ))
    return results


def search_pubmed(query: str, limit: int, mode: str):
    """PubMed E-utilities 两步搜索（esearch 取 PMID → esummary 取详情）。免费无 Key。

    生物医学领域必备。PubMed 本身不提供全文 PDF，只返回 PMID + 标题/作者/期刊/摘要；
    拿到 DOI 后可走下载接口（多数生物医学论文也有开放获取版本）。
    NCBI 建议 3 RPS，_get_with_retry 的重试间隔能覆盖瞬时限流。
    """
    # 第一步：esearch 拿 PMID 列表
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": min(limit, 100),
        "retmode": "json",
        "sort": "relevance",
    }
    resp = _get_with_retry(PUBMED_ESUMMARY_URL.replace("esummary", "esearch"), params, timeout=20)
    try:
        data = resp.json()
    except ValueError as e:
        raise RuntimeError(f"PubMed esearch 返回了无法解析的内容: {e}")
    id_list = data.get("esearchresult", {}).get("idlist", []) or []
    if not id_list:
        return []

    # 第二步：esummary 批量取详情
    summ_params = {"db": "pubmed", "id": ",".join(id_list), "retmode": "json"}
    resp2 = _get_with_retry(PUBMED_ESUMMARY_URL, summ_params, timeout=20)
    try:
        sdata = resp2.json()
    except ValueError as e:
        raise RuntimeError(f"PubMed esummary 返回了无法解析的内容: {e}")
    result_obj = sdata.get("result", {})
    uids = result_obj.get("uids", []) or []

    results = []
    for uid in uids:
        rec = result_obj.get(uid, {}) or {}
        authors = [a.get("name", "") for a in (rec.get("authors") or [])][:6]
        # 从 articleids 里提取 DOI（如果有）
        doi = None
        for aid in rec.get("articleids") or []:
            if aid.get("idtype") == "doi":
                doi = aid.get("value")
                break
        results.append(_norm_result(
            title=rec.get("title"),
            authors=authors,
            published=rec.get("pubdate"),
            abstract=None,  # esummary 不含摘要，需 efetch；摘要质量对搜索展示非必需，省一次请求
            venue=rec.get("fulljournalname") or rec.get("source"),
            doi=doi,
            pmid=uid,
            page_url=f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
            source="pubmed",
        ))
    return results


# 来源优先级：用于聚合去重后排序（被多平台收录的排前，同分时按此优先级）
# S2/OpenAlex 元数据质量最高，arXiv 次之，Crossref/PubMed 补充。
_SOURCE_PRIORITY = {"semantic_scholar": 0, "openalex": 1, "arxiv": 2, "crossref": 3, "pubmed": 4}
# multi 聚合默认查询的源（排除限流敏感的 S2：多源并发会加剧其 429）
_MULTI_SOURCES = ["openalex", "crossref", "arxiv"]


def _dedup_key(p: dict) -> str | None:
    """生成去重键。优先用稳定标识符（DOI/arXiv/PMID），都没有才退而用标题归一化。"""
    if p.get("doi"):
        return f"doi:{p['doi'].strip().lower()}"
    if p.get("arxiv_id"):
        return f"arxiv:{re.sub(r'v\d+$', '', p['arxiv_id'].strip().lower())}"
    if p.get("pmid"):
        return f"pmid:{p['pmid'].strip()}"
    # 标题兜底：小写 + 去标点/空格，避免因大小写/空格差异误判为不同论文
    title = p.get("title") or ""
    norm = re.sub(r"[^\w]", "", title.lower())
    return f"title:{norm}" if norm else None


def _merge_results(per_source: dict, limit: int) -> list:
    """把多个平台的结果合并去重。

    排序策略（保证 multi 模式能看到各平台的代表性结果，而非只看到优先级最高的源）：
    1. 先去重：同一篇被多平台收录时合并，保留信息最完整的记录。
    2. 多源命中的论文绝对优先（被多平台收录=更可能是核心文献）。
    3. 其余按来源轮转（round-robin）：按 OA[1]→CR[1]→arXiv[1]→OA[2]→... 交替，
       确保每个平台都有代表进入结果，而非高优先源独占前几名。
    """
    groups: dict[str, dict] = {}
    for src, results in per_source.items():
        for rank, p in enumerate(results):
            key = _dedup_key(p)
            if not key:
                continue
            if key not in groups:
                groups[key] = {
                    "best": p, "hits": 0, "sources": set(),
                    # 记录在各源中的最早排名，用于轮转排序
                    "first_rank": rank, "first_source": src,
                }
            g = groups[key]
            g["hits"] += 1
            g["sources"].add(src)
            if _result_richness(p) > _result_richness(g["best"]):
                g["best"] = p

    # 多源命中的优先输出，其余按轮转分组
    multi_hit, single = [], []
    for g in groups.values():
        (multi_hit if g["hits"] > 1 else single).append(g)
    # 多源命中按命中数降序
    multi_hit.sort(key=lambda g: -g["hits"])
    # 单源命中按 (轮转位置=各源内排名, 来源优先级) 排序——来源优先级决定轮转起始顺序
    single.sort(key=lambda g: (g["first_rank"], _SOURCE_PRIORITY.get(g["first_source"], 9)))

    merged = []
    seen = set()
    for g in multi_hit + single:
        p = dict(g["best"])
        if g["hits"] > 1:
            p["matched_sources"] = sorted(g["sources"])
        merged.append(p)
        seen.add(_dedup_key(p))
    return merged[:limit] if limit else merged


def _result_richness(p: dict) -> int:
    """结果信息丰度评分：用于去重时保留字段更完整的记录。"""
    score = 0
    if p.get("abstract"):
        score += 4
    if p.get("pdf_url"):
        score += 3
    if p.get("doi"):
        score += 2
    if p.get("arxiv_id"):
        score += 1
    if p.get("venue"):
        score += 1
    return score


def run_search(query: str, limit: int, mode: str, source: str):
    # multi: 多平台聚合查询，结果合并去重（被多平台收录的排前）
    if source == "multi":
        return _run_multi_search(query, limit, mode)

    # 单源直接走
    if source == "arxiv":
        return search_arxiv(query, limit, mode)
    if source == "semanticscholar":
        return search_semantic_scholar(query, limit, mode)
    if source == "openalex":
        return search_openalex(query, limit, mode)
    if source == "crossref":
        return search_crossref(query, limit, mode)
    if source == "pubmed":
        return search_pubmed(query, limit, mode)

    # auto: 多源串联，首个返回非空结果的源即用，避免单一平台限流/无数据阻断
    # 优先级：Semantic Scholar（覆盖广）→ OpenAlex（含 OA PDF）→ arXiv（预印本，纯预印本话题命中率高）
    for src_name, src_fn in [
        ("Semantic Scholar", search_semantic_scholar),
        ("OpenAlex", search_openalex),
        ("arXiv", search_arxiv),
    ]:
        try:
            results = src_fn(query, limit, mode)
            if results:
                return results
            print(f"[提示] {src_name} 没有搜到结果，尝试下一个源...", file=sys.stderr)
        except Exception as e:
            print(f"[提示] {src_name} 搜索失败（{e}），尝试下一个源...", file=sys.stderr)
    return []


def _run_multi_search(query: str, limit: int, mode: str):
    """多平台聚合搜索：串行查多个源，合并去重，被多平台收录的排前。

    串行而非并发——避免 S2/OpenAlex 等被并发请求触发限流（429）。各源各自重试，
    单个源失败不影响其他源。每源各取 limit 篇，去重后可能远超 limit，覆盖面最广。
    """
    sources = {
        "openalex": ("OpenAlex", search_openalex),
        "crossref": ("Crossref", search_crossref),
        "arxiv": ("arXiv", search_arxiv),
    }
    per_source: dict = {}
    ok_sources = []
    for key, (name, fn) in sources.items():
        try:
            results = fn(query, limit, mode)
            if results:
                per_source[key] = results
                ok_sources.append(name)
            else:
                print(f"[提示] {name} 无结果", file=sys.stderr)
        except Exception as e:
            print(f"[提示] {name} 失败（{e}）", file=sys.stderr)
    if not per_source:
        return []
    total = sum(len(v) for v in per_source.values())
    print(f"[聚合] 成功查询 {', '.join(ok_sources)}，共取到 {total} 条，去重中...", file=sys.stderr)
    return _merge_results(per_source, limit)


def format_human(results):
    if not results:
        return "未找到相关论文。可以换个更宽泛的关键词，或用 --source 明确指定某个平台（openalex/crossref/pubmed/arxiv）单独试试。"
    lines = []
    for i, p in enumerate(results, 1):
        lines.append(f"[{i}] {p['title'] or '（无标题）'}")
        if p.get("authors"):
            shown = p["authors"][:6]
            lines.append(f"    作者: {', '.join(shown)}" + (" 等" if len(p["authors"]) > 6 else ""))
        venue_info = p.get('venue') or p.get('source')
        # multi 聚合时，被多平台收录的论文标注“N 源命中”，供用户判断相关性/可信度
        matched = p.get('matched_sources')
        if matched and len(matched) > 1:
            venue_info += f"    ★{len(matched)}源命中({', '.join(matched)})"
        lines.append(f"    发表时间: {p.get('published') or '未知'}    来源: {venue_info}")
        ids = []
        if p.get("arxiv_id"):
            ids.append(f"arXiv:{p['arxiv_id']}")
        if p.get("doi"):
            ids.append(f"DOI:{p['doi']}")
        if p.get("pmid"):
            ids.append(f"PMID:{p['pmid']}")
        if p.get("semantic_scholar_id"):
            ids.append(f"S2:{p['semantic_scholar_id']}")
        if ids:
            lines.append(f"    标识: {' | '.join(ids)}")
        if p.get("pdf_url"):
            lines.append(f"    PDF: {p['pdf_url']}")
        abstract = (p.get("abstract") or "").strip().replace("\n", " ")
        if abstract:
            snippet = abstract[:280] + ("..." if len(abstract) > 280 else "")
            lines.append(f"    摘要: {snippet}")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="学术论文搜索")
    ap.add_argument("query", help="搜索的主题关键词，或论文标题（配合 --mode title）")
    ap.add_argument("--mode", choices=["topic", "title"], default="topic", help="搜索模式：topic=主题关键词，title=论文标题")
    ap.add_argument("--source", choices=["auto", "multi", "semanticscholar", "openalex", "crossref", "pubmed", "arxiv"], default="auto", help="搜索源：auto=依次降级(S2→OpenAlex→arXiv)；multi=多平台聚合去重(覆盖最广)；也可单指定 openalex/crossref/pubmed/arxiv/semanticscholar")
    ap.add_argument("--limit", type=int, default=20, help="返回结果数量，默认 20（multi 模式下去重后可能不足此数，取决于多源重叠程度）")
    ap.add_argument("--json", action="store_true", help="以 JSON 格式输出（供程序处理），默认人类可读格式")
    args = ap.parse_args()

    if args.limit <= 0:
        print("错误: --limit 必须是正整数", file=sys.stderr)
        sys.exit(1)

    try:
        results = run_search(args.query, args.limit, args.mode, args.source)
    except Exception as e:
        print(f"错误: 搜索失败 — {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(format_human(results))


if __name__ == "__main__":
    main()
