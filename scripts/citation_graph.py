#!/usr/bin/env python3
"""
citation_graph.py — OpenCitations 引用关系查询（接口三·引用图谱）

按 DOI 查询 OpenCitations（CC0 协议）的引用边，供两个场景使用：
  - paper 模块 citation-check：核对论文自身参考文献是否与官方引用记录一致（references 方向）
  - reviewer 模块证据核验：查一篇论文被谁引用、引用语境是否随时间变化（citations 方向）

OpenCitations 不做关键词检索，只做 DOI → 引用边的确定性查询；这是它与 search_papers.py
分工的边界：检索找论文，本脚本核引用。

数据源说明：
  - citations（入边）：谁引用了这篇论文（citing → 本 DOI）
  - references（出边）：这篇论文引用了谁（本 DOI → cited）
  - COCI 索引以 Crossref/OpenAlex 收录为前提，ChinaXiv 等 ISTIC 注册 DOI 查不到（返回空，不是错误）

用法：
    python citation_graph.py 10.1145/3025453.3025717
    python citation_graph.py doi:10.1145/3025453.3025717 --direction references
    python citation_graph.py https://doi.org/10.1145/3025453.3025717 --direction citations --json

环境变量（一般不需要设置，测试时覆盖）：
    OPENCITATIONS_API_URL 默认 https://opencitations.net/index/api/v2
"""

import argparse
import json
import os
import re
import sys
import time

import requests

OPENCITATIONS_API_URL = os.environ.get("OPENCITATIONS_API_URL", "https://opencitations.net/index/api/v2")

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 1.5

DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")


def _get_with_retry(url: str, timeout: int = 20) -> requests.Response:
    """重试瞬时错误后返回响应。

    与 search_papers.py 的变体不同：404 不抛 HTTPError 而是原样返回——
    OpenCitations 对未收录 DOI 返回 404 是「正常空结果」（见 docstring 与
    api_notes.md），由 fetch_edges 统一转空列表；其余 4xx/5xx 仍抛。
    """
    last_exc = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=timeout, headers={"User-Agent": "liuxiang/1.0"})
            if resp.status_code == 404:
                return resp
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


def normalize_doi(identifier: str) -> str:
    """接受裸 DOI / doi: 前缀 / https://doi.org/ 链接，统一为裸 DOI。"""
    text = identifier.strip()
    m = re.match(r"^https?://(?:dx\.)?doi\.org/(10\..+)$", text, re.IGNORECASE)
    if m:
        text = m.group(1)
    text = re.sub(r"^doi:", "", text, flags=re.IGNORECASE)
    text = text.strip()
    if not DOI_RE.match(text):
        raise RuntimeError(f"无法识别的 DOI：{identifier!r}（期望 10.xxxx/... 形式）。")
    return text


def fetch_edges(doi: str, direction: str) -> list:
    """查询引用边。direction: citations（入边）/ references（出边）。

    返回 OpenCitations 原始边列表：[{oci, citing, cited, creation, timespan, journal_sc, author_sc}]。
    """
    endpoint = "citations" if direction == "citations" else "references"
    url = f"{OPENCITATIONS_API_URL}/{endpoint}/doi:{doi}"
    resp = _get_with_retry(url)
    if resp.status_code == 404 or not resp.text.strip():
        # 未收录 DOI（ISTIC 注册如 ChinaXiv 10.12074、极新论文）的 404 是正常空结果
        return []
    try:
        data = resp.json()
    except ValueError as e:
        raise RuntimeError(f"OpenCitations 返回了无法解析的内容: {e}")
    if isinstance(data, dict):
        # v2 对不存在的 DOI 返回 {} 或 {"error": ...}，统一按空处理
        return []
    return data


def summarize_edges(edges: list, doi: str, direction: str, top: int = 20) -> list:
    """把边整理为人类可读的行。citations 方向看 citing，references 方向看 cited。"""
    other = "citing" if direction == "citations" else "cited"
    rows = []
    for e in edges:
        ident = e.get(other, "")
        # 提取纯 DOI（omid:/openalex:/arxiv: 等命名空间取 doi: 部分，无 DOI 则保留原样）
        m = re.search(r"doi:(10\.\S+)", ident)
        other_doi = m.group(1) if m else ident
        rows.append({
            "oci": e.get("oci"),
            "identifier": other_doi,
            "year": (e.get("creation") or "")[:4] or None,
            "timespan": e.get("timespan"),
        })
    return rows[:top]


def format_human(doi: str, citations: list, references: list) -> str:
    lines = [f"DOI: {doi}", ""]
    lines.append(f"被引（citations，{len(citations)} 条，最多展示前 {min(len(citations), 20)} 条）：")
    if citations:
        for r in citations:
            lines.append(f"  [{r['year'] or '????'}] {r['identifier']}  (oci: {r['oci']}, 距今 {r['timespan']})")
    else:
        lines.append("  （COCI 未收录该 DOI 的被引记录——新论文或非 Crossref 注册 DOI 均会如此，不是错误）")
    lines.append("")
    lines.append(f"参考文献（references，{len(references)} 条，最多展示前 {min(len(references), 20)} 条）：")
    if references:
        for r in references:
            lines.append(f"  [{r['year'] or '????'}] {r['identifier']}  (oci: {r['oci']})")
    else:
        lines.append("  （COCI 未收录该 DOI 的参考文献记录）")
    lines.append("")
    lines.append("提示：完整边列表用 --json 获取；oci 字段可用于 OpenCitations 的溯源。")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="OpenCitations 引用关系查询（DOI → 引用边）")
    ap.add_argument("identifier", help="DOI（支持裸 DOI / doi: 前缀 / doi.org 链接）")
    ap.add_argument("--direction", choices=["citations", "references", "both"], default="both",
                    help="citations=谁引用了它；references=它引用了谁；默认 both")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出（供程序处理），默认人类可读")
    args = ap.parse_args()

    try:
        doi = normalize_doi(args.identifier)
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        citations = fetch_edges(doi, "citations") if args.direction in ("citations", "both") else []
        references = fetch_edges(doi, "references") if args.direction in ("references", "both") else []
    except Exception as e:
        print(f"错误: 引用查询失败 — {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps({
            "doi": doi,
            "citations": citations,
            "references": references,
        }, ensure_ascii=False, indent=2))
    else:
        cit_rows = summarize_edges(citations, doi, "citations")
        ref_rows = summarize_edges(references, doi, "references")
        print(format_human(doi, cit_rows, ref_rows))


if __name__ == "__main__":
    main()
