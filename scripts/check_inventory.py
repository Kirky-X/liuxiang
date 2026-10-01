#!/usr/bin/env python3
"""
check_inventory.py — 文档数字对账守卫（磁盘实数为唯一事实源）

README.md / README_EN.md / SKILL.md 里的每一个数字声明（N-agent / N 模式 / N 数据源 /
N 阶段 / N 论文类型 / N 引用格式）都必须与磁盘实况一致，不一致即 CI 拒绝合并。
本脚本曾对应的历史事故：README 与实测矛盾（orchestra 仓库同款漂移）、SKILL.md 内联
模式清单漏列模式——这类漂移靠人眼盯不住，靠脚本 fail-closed。

事实源推导：
  paper/reviewer/pipeline 的 agent 数   解析 reference/<module>.md 的 Agent Team 表行数
  paper/reviewer 的模式数               解析 reference/<module>.md 的 Operational Modes 表行数
  pipeline 阶段数                       解析 reference/pipeline.md 的 Pipeline Stages 表行数
  search 数据源数                       解析 scripts/search_papers.py 的 --source choices（剔除 auto/multi）
  论文类型数                            解析 references/paper_structure_patterns.md 的 "## Pattern N:" 标题
  引用格式数                            解析 reference/paper.md § Citation Formats 段的逗号项数
  agent 总数                            agents/*.md 文件计数

用法：
    python3 scripts/check_inventory.py [--root 仓库根目录] [--json]
退出码：0 = 全部一致；1 = 存在漂移（CI 阻断）；2 = 用法/文件错误。
"""

import argparse
import json
import os
import re
import sys

import mdtables

# (事实键, [(相对路径, 正则（含一个捕获组）, 行上下文锚点或 None)], 说明)
# 正则锚定到当前文档措辞；措辞演进时此处同步更新——这正是对账契约的一部分。
NUMERIC_CHECKS = [
    ("paper_agents", [
        ("SKILL.md", r"(\d+)-agent 论文写作", None),
        ("README.md", r"(\d+)-agent 论文写作", None),
        ("README_EN.md", r"(\d+)-agent paper writing", None),
    ], "paper 模块 agent 数"),
    ("paper_modes", [
        ("SKILL.md", r"论文写作，(\d+) 模式", None),
        ("README.md", r"论文写作 \| (\d+) 种模式", None),
        ("README_EN.md", r"paper writing \| (\d+) modes", None),
    ], "paper 模块模式数"),
    ("paper_types", [
        ("SKILL.md", r"论文写作，\d+ 模式，(\d+) 论文类型", None),
        ("README.md", r"(\d+) 论文类型", None),
        ("README_EN.md", r"(\d+) paper types", None),
    ], "论文类型数"),
    ("citation_formats", [
        ("SKILL.md", r"论文写作，\d+ 模式，\d+ 论文类型，(\d+) 引用格式", None),
        ("README.md", r"(\d+) 引用格式", None),
        ("README_EN.md", r"(\d+) citation formats", None),
    ], "引用格式数"),
    ("reviewer_agents", [
        ("SKILL.md", r"(\d+)-agent 多视角同行评审", None),
        ("README.md", r"(\d+)-agent 多视角同行评审", None),
        ("README_EN.md", r"(\d+)-agent multi-perspective peer review", None),
    ], "reviewer 模块 agent 数"),
    ("reviewer_modes", [
        ("SKILL.md", r"多视角同行评审，(\d+) 模式", None),
        ("README.md", r"多视角同行评审 \| (\d+) 种模式", None),
        ("README_EN.md", r"peer review \| (\d+) modes", None),
    ], "reviewer 模块模式数"),
    ("pipeline_stages", [
        ("SKILL.md", r"端到端 (\d+) 阶段流水线", None),
        ("README.md", r"端到端 (\d+) 阶段流水线", None),
        ("README_EN.md", r"End-to-end (\d+)-stage pipeline", None),
    ], "pipeline 阶段数"),
    ("agents_total", [
        ("README.md", r"(\d+) 个 agent", None),
    ], "agents/ 定义文件总数"),
]

# 列表型声明：括号内枚举必须与磁盘实况集合一致（顺序不敏感，名字按前缀匹配容忍缩写）
# group：正则中承载清单内容的捕获组序号
LIST_CHECKS = [
    ("paper_modes", "SKILL.md", r"论文写作（([a-z-/]+)）", 1, "SKILL.md 内联 paper 模式清单"),
    ("search_sources", "SKILL.md", r"脚本驱动（([^）]+?) 多源", 1, "SKILL.md 内联检索源清单"),
    ("search_sources", "README.md", r"\d+ 个数据源：([^，。|]+)", 1, "README.md 内联检索源清单"),
    ("search_sources", "README_EN.md", r"\d+ sources: ([^;|]+)", 1, "README_EN.md 内联检索源清单"),
]

MODE_SHORT_ALIASES = {
    "outline": "outline-only",
    "abstract": "abstract-only",
    "revision": "revision",
}


def _read(root: str, rel: str) -> str:
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        raise RuntimeError(f"对账目标不存在: {path}")
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# 事实源推导
# ---------------------------------------------------------------------------
def _table_rows_after(text: str, heading_pattern: str) -> list:
    return mdtables.table_rows_after(text, heading_pattern)


def derive_truth(root: str) -> dict:
    paper = _read(root, "reference/paper.md")
    reviewer = _read(root, "reference/reviewer.md")
    pipeline = _read(root, "reference/pipeline.md")

    agents_dir = os.path.join(root, "agents")
    agents_total = len([fn for fn in os.listdir(agents_dir) if fn.endswith(".md")])

    def agent_count(doc: str) -> int:
        rows = _table_rows_after(doc, r"^## Agent Team\b.*$", )
        return sum(1 for r in rows if r and re.match(r"^\d+$", r[0]))

    def mode_names(doc: str) -> list:
        rows = _table_rows_after(doc, r"^## Operational Modes\b.*$")
        names = []
        for r in rows:
            if r and "`" in r[0]:
                m = re.search(r"`([a-z-]+)`", r[0])
                if m:
                    names.append(m.group(1))
        return names

    stage_rows = _table_rows_after(pipeline, r"^## Pipeline Stages \(10 Stages\)\s*$")
    stages = [r for r in stage_rows if r and re.match(r"^[\d.']+$", r[0].strip("*"))]

    search_src = _read(root, "scripts/search_papers.py")
    choices_m = re.search(r'add_argument\("--source", choices=\[([^\]]+)\]', search_src)
    if not choices_m:
        raise RuntimeError("无法从 search_papers.py 解析 --source choices")
    sources = [s.strip().strip("\"'") for s in choices_m.group(1).split(",")]
    sources = [s for s in sources if s not in ("auto", "multi")]

    patterns_doc = _read(root, "references/paper_structure_patterns.md")
    paper_types = len(re.findall(r"^## Pattern \d+:", patterns_doc, re.MULTILINE))

    cite_m = re.search(r"### Citation Formats\s*\n\n([^\n]+)", paper)
    citation_formats = 0
    if cite_m:
        items = [i.strip() for i in cite_m.group(1).rstrip(". ").split(", ") if i.strip()]
        citation_formats = len(items)

    return {
        "paper_agents": agent_count(paper),
        "reviewer_agents": agent_count(reviewer),
        "pipeline_agents": agent_count(pipeline),
        "agents_total": agents_total,
        "paper_modes_list": mode_names(paper),
        "reviewer_modes_list": mode_names(reviewer),
        "paper_modes": len(mode_names(paper)),
        "reviewer_modes": len(mode_names(reviewer)),
        "pipeline_stages": len(stages),
        "search_sources": len(sources),
        "search_sources_list": sources,
        "paper_types": paper_types,
        "citation_formats": citation_formats,
    }


# ---------------------------------------------------------------------------
# 声明核验
# ---------------------------------------------------------------------------
def check_numeric(claims_text: str, pattern: str, expected: int, where: str, errors: list) -> int:
    """返回命中次数；每个命中数字都必须等于 expected，否则记错误。"""
    hits = re.findall(pattern, claims_text, re.MULTILINE)
    if not hits:
        errors.append(f"{where}: 未找到声明（模式 {pattern!r}）——声明被删改时守卫必须失败")
        return 0
    for h in hits:
        got = int(h)
        if got != expected:
            errors.append(f"{where}: 声明为 {got}，磁盘实数 {expected}（模式 {pattern!r}）")
    return len(hits)


def normalize_mode_name(name: str) -> str:
    return MODE_SHORT_ALIASES.get(name.strip(), name.strip())


def check_mode_list(inline: str, expected_modes: list, where: str, errors: list) -> None:
    listed = [normalize_mode_name(x) for x in inline.split("/") if x.strip()]
    expected_set = set(expected_modes)
    listed_set = set(listed)
    missing = expected_set - listed_set
    extra = listed_set - expected_set
    # 前缀容忍：SKILL.md 内联表用缩写（outline-only→outline）
    unresolved_extra = []
    for name in extra:
        if not any(m.startswith(name) or name.startswith(m) for m in expected_set):
            unresolved_extra.append(name)
    if missing or unresolved_extra:
        errors.append(f"{where}: 内联清单与模式表不一致——缺 {sorted(missing)}，多 {sorted(unresolved_extra)}（磁盘模式表：{sorted(expected_set)}）")


def check_source_list(inline: str, expected_sources: list, where: str, errors: list) -> None:
    names = [x.strip() for x in re.split(r"[/；;]", inline) if x.strip()]
    # 文档用展示名（OpenAlex / Europe PMC），脚本用源键（openalex/europmc）
    display_map = {
        "semanticscholar": ["semantic scholar", "semanticscholar"],
        "openalex": ["openalex"],
        "arxiv": ["arxiv"],
        "dblp": ["dblp"],
        "europmc": ["europe pmc", "europmc"],
        "crossref": ["crossref"],
        "pubmed": ["pubmed"],
        "core": ["core"],
        "openaire": ["openaire"],
    }
    lower_names = [n.lower() for n in names]
    for key in expected_sources:
        if not any(alias in lower_names for alias in display_map.get(key, [key])):
            errors.append(f"{where}: 检索源清单缺少 {key}（现有：{names}）")
    if len(names) != len(expected_sources):
        errors.append(f"{where}: 清单列出 {len(names)} 个源，磁盘实数 {len(expected_sources)}")


def run_checks(root: str) -> dict:
    truth = derive_truth(root)
    errors, hits = [], []

    for key, targets, desc in NUMERIC_CHECKS:
        expected = truth.get(key)
        for rel, pattern, anchor in targets:
            text = _read(root, rel)
            lines = text.split("\n")
            if anchor:
                scoped = "\n".join(l for l in lines if re.search(anchor, l))
                n = check_numeric(scoped, pattern, expected, f"{rel}", errors)
            else:
                n = check_numeric(text, pattern, expected, rel, errors)
            if n:
                hits.append(f"{rel}: {key}={expected}（{n} 处声明一致）")

    for key, rel, pattern, group, desc in LIST_CHECKS:
        text = _read(root, rel)
        m = re.search(pattern, text, re.DOTALL)
        if not m:
            errors.append(f"{rel}: 未找到列表型声明（{desc}）")
            continue
        expected_list = truth["paper_modes_list"] if key == "paper_modes" else truth["search_sources_list"]
        if key == "paper_modes":
            check_mode_list(m.group(group), expected_list, rel, errors)
        else:
            check_source_list(m.group(group), expected_list, rel, errors)
        hits.append(f"{rel}: {desc}")

    # agents/ 文件计数与各模块 agent 表之和必须自洽
    module_sum = truth["paper_agents"] + truth["reviewer_agents"] + truth["pipeline_agents"]
    if module_sum != truth["agents_total"]:
        errors.append(
            f"agents/ 目录有 {truth['agents_total']} 个文件，但三个模块 Agent Team 表合计 {module_sum}"
            f"（paper {truth['paper_agents']} + reviewer {truth['reviewer_agents']} + pipeline {truth['pipeline_agents']}）"
        )

    return {"pass": not errors, "truth": truth, "errors": errors, "consistent_claims": hits}


def main():
    ap = argparse.ArgumentParser(description="文档数字对账守卫（磁盘实数 vs README/SKILL 声明）")
    ap.add_argument("--root", default=None, help="仓库根目录（默认：脚本上级目录）")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = args.root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        result = run_checks(root)
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(2)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("磁盘实数：", json.dumps(result["truth"], ensure_ascii=False))
        for h in result["consistent_claims"]:
            print(f"  ✓ {h}")
        for e in result["errors"]:
            print(f"  ✗ {e}")
        print("对账通过。" if result["pass"] else "对账失败：以上声明与磁盘实数不一致，先修正文档或代码。")

    sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
