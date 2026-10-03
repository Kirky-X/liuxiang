#!/usr/bin/env python3
"""
check_latex.py — LaTeX 编译前机械四查（确定性预检，模型只负责修不负责判）

四类编译前检查（借鉴 AI-Scientist 的 generate_latex 编译门禁，改为独立可测的脚本）：
  1. 缺失引用：正文 \\cite/\\citep/\\citet... 用到的 key 对照 .bib 定义
  2. 缺失图片：\\includegraphics 引用的图文件在磁盘上不存在
  3. 重复插图：同一图文件被 \\includegraphics 引用多次（编译能过但占版面/审稿观感差）
  4. 重复章节：同级同名 \\section/\\subsection 重复出现

可选 --chktex 追加一轮 chktex 静态检查（安装了 chktex 二进制才生效），
默认抑制噪声告警 ID 2/24/13/1（与 AI-Scientist 抑噪清单一致）。

定位：本脚本只做确定性判断，产出结构化问题清单；**修订由 formatter_agent 读清单后改写**，
改完重跑本脚本直到清零——这个「检查→修订→复检」循环属于 format-convert 模式与
pipeline Stage 5 的编排逻辑，不在本脚本内。

用法：
    python check_latex.py main.tex
    python check_latex.py paper/ --bib refs/main.bib
    python check_latex.py main.tex --chktex --json

退出码：0 = 无问题；1 = 有问题（清单见 stdout）；2 = 用法/文件错误。
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

# chktex 噪声抑制默认清单（ID 含义：2=命令未换行对齐、24=引号风格、13=标点后空格、1=命令终止缺空格）
CHKTEX_DEFAULT_SUPPRESS = [2, 24, 13, 1]

IMG_RESOLVE_EXTS = ["", ".pdf", ".png", ".jpg", ".jpeg", ".eps"]

CITE_CMD_RE = re.compile(
    r"\\(?:cite|citep|citet|citealp|citealt|citeauthor|citeyear|Citep|Citet|citeal)\*?"
    r"(?:\[[^\]]*\]){0,2}\{([^}]+)\}"
)
FIG_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")
SECTION_RE = re.compile(r"\\(section|subsection|subsubsection)\*?\{([^}]+)\}")
BIB_ENTRY_RE = re.compile(r"@\w+\{\s*([^,\s{}]+)\s*,")
INPUT_RE = re.compile(r"\\(?:input|include)\{([^}]+)\}")


def strip_comments(tex: str) -> str:
    """去掉 % 注释（保留 \\% 转义）。多行注释场景按行处理。"""
    lines = []
    for line in tex.split("\n"):
        out = []
        i = 0
        while i < len(line):
            if line[i] == "\\" and i + 1 < len(line):
                out.append(line[i:i + 2])
                i += 2
                continue
            if line[i] == "%":
                break
            out.append(line[i])
            i += 1
        lines.append("".join(out))
    return "\n".join(lines)


def expand_inputs(tex_path: str, _seen: set | None = None) -> str:
    """递归展开 \\input/\\include，返回合并后的完整 LaTeX 源（多文件论文场景）。"""
    if _seen is None:
        _seen = set()
    real = os.path.realpath(tex_path)
    if real in _seen:
        return ""
    _seen.add(real)
    try:
        with open(tex_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except OSError as e:
        print(f"[提示] 无法读取 {tex_path}: {e}", file=sys.stderr)
        return ""

    base_dir = os.path.dirname(os.path.abspath(tex_path))

    def repl(m):
        target = m.group(1).strip()
        if not target.endswith(".tex"):
            target += ".tex"
        # 路径围栏：拒绝绝对路径与 .. 穿越，展开结果必须仍在论文目录内
        sub = os.path.normpath(os.path.join(base_dir, target))
        if os.path.isabs(target) or not sub.startswith(os.path.abspath(base_dir) + os.sep):
            print(f"[提示] \\input 目标越出论文目录，已拒绝: {target}", file=sys.stderr)
            return ""
        if os.path.isfile(sub):
            return "\n" + expand_inputs(sub, _seen) + "\n"
        print(f"[提示] \\input 目标不存在，已跳过: {sub}", file=sys.stderr)
        return ""

    return INPUT_RE.sub(repl, content)


def collect_cited_keys(tex: str) -> list:
    keys = []
    for m in CITE_CMD_RE.finditer(tex):
        for k in m.group(1).split(","):
            k = k.strip()
            if k:
                keys.append(k)
    return keys


def collect_bib_keys(bib_path: str) -> list:
    try:
        with open(bib_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except OSError as e:
        print(f"[提示] 无法读取 bib 文件 {bib_path}: {e}", file=sys.stderr)
        return []
    keys = []
    for m in BIB_ENTRY_RE.finditer(content):
        key = m.group(1)
        if key.lower() in ("string", "comment", "preamble"):
            continue
        keys.append(key)
    return keys


def find_bib_files(target: str, explicit: list) -> list:
    if explicit:
        return list(explicit)
    base = target if os.path.isdir(target) else os.path.dirname(os.path.abspath(target))
    return sorted(
        os.path.join(base, fn) for fn in os.listdir(base) if fn.endswith(".bib")
    )


def resolve_figure_path(raw: str, base_dir: str) -> str | None:
    """按 includegraphics 的原始引用解析图文件真实路径；找不到返回 None。"""
    raw = raw.strip().replace("\\", "/")
    candidates = []
    if os.path.isabs(raw):
        candidates.append(raw)
        stem, ext = os.path.splitext(raw)
        if not ext:
            candidates += [stem + e for e in IMG_RESOLVE_EXTS if e]
    else:
        base = os.path.join(base_dir, raw)
        candidates.append(base)
        stem, ext = os.path.splitext(base)
        if not ext:
            candidates += [stem + e for e in IMG_RESOLVE_EXTS if e]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def check_missing_citations(tex: str, bib_files: list) -> dict:
    cited = collect_cited_keys(tex)
    defined = []
    for b in bib_files:
        defined += collect_bib_keys(b)
    defined_set = set(defined)
    missing = sorted({k for k in cited if k not in defined_set})
    uncited = sorted(k for k in defined if k not in set(cited))
    return {
        "check": "missing_citations",
        "severity": "error" if missing else "clean",
        "cited_total": len(cited),
        "bib_total": len(defined),
        "missing_keys": missing,
        "uncited_bib_entries": uncited,
        "detail": [f"引用 key 未在 .bib 中定义: {k}" for k in missing],
    }


def check_figures(tex: str, base_dir: str) -> dict:
    refs = [m.group(1).strip() for m in FIG_RE.finditer(tex)]
    missing = []
    for raw in refs:
        if resolve_figure_path(raw, base_dir) is None:
            missing.append(raw)
    dup = sorted({raw for raw in refs if refs.count(raw) > 1})
    return {
        "check": "figures",
        "severity": "error" if missing else ("warning" if dup else "clean"),
        "includegraphics_total": len(refs),
        "missing_files": missing,
        "duplicate_includes": dup,
        "detail": (
            [f"\\includegraphics 文件不存在: {m}" for m in missing]
            + [f"图被重复引用: {d}（{refs.count(d)} 次）" for d in dup]
        ),
    }


def _norm_section_title(title: str) -> str:
    text = re.sub(r"\\[a-zA-Z]+", " ", title)
    text = re.sub(r"[{}$]", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def check_duplicate_sections(tex: str) -> dict:
    seen: dict = {}
    dups = []
    for m in SECTION_RE.finditer(tex):
        level, title = m.group(1), m.group(2)
        norm = _norm_section_title(title)
        key = f"{level}:{norm}"
        if key in seen and key not in dups and norm:
            dups.append(key)
        seen.setdefault(key, title.strip())
    return {
        "check": "duplicate_sections",
        "severity": "warning" if dups else "clean",
        "duplicates": dups,
        "detail": [
            f"同名同级章节重复: {key.split(':', 1)[1]}（{key.split(':', 1)[0]}，首次出现于 \"{seen[key]}\"）"
            for key in dups
        ],
    }


def run_chktex(tex_path: str, suppress: list) -> dict:
    """跑一轮 chktex（若二进制可用）；不可用返回 skipped，不阻断。"""
    binary = shutil.which("chktex")
    if not binary:
        return {
            "check": "chktex",
            "severity": "skipped",
            "detail": ["chktex 未安装，跳过（apt/brew 安装 chktex 后可用 --chktex 启用）"],
            "warnings": [],
        }
    cmd = [binary, "-q", "-I"]
    for sid in suppress:
        cmd.append(f"-n{sid}")
    cmd.append(tex_path)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"check": "chktex", "severity": "skipped", "detail": [f"chktex 运行失败: {e}"], "warnings": []}
    warnings = []
    for line in (proc.stdout or "").split("\n"):
        m = re.match(r"(?:Warning|Error)\s+(\d+)\s+in\s+(\d+),\s*line\s+(\d+):\s*(.*)", line.strip())
        if m:
            warnings.append({
                "type": int(m.group(1)),
                "message": m.group(4).strip(),
                "line": int(m.group(3)),
            })
    return {
        "check": "chktex",
        "severity": "warning" if warnings else "clean",
        "suppressed_ids": suppress,
        "warnings": warnings,
        "detail": [f"chktex W{w['type']} L{w['line']}: {w['message']}" for w in warnings],
    }


def run_checks(target: str, bib_files: list, with_chktex: bool, chktex_suppress: list) -> list:
    if os.path.isdir(target):
        main_tex = None
        for pref in ("main.tex", "paper.tex", "ms.tex", "article.tex"):
            p = os.path.join(target, pref)
            if os.path.isfile(p):
                main_tex = p
                break
        if main_tex is None:
            texs = sorted(fn for fn in os.listdir(target) if fn.endswith(".tex"))
            if not texs:
                raise RuntimeError(f"目录 {target} 中没有 .tex 文件。")
            main_tex = os.path.join(target, texs[0])
    elif os.path.isfile(target):
        main_tex = target
    else:
        raise RuntimeError(f"目标不存在: {target}")

    tex = strip_comments(expand_inputs(main_tex))
    base_dir = os.path.dirname(os.path.abspath(main_tex))

    results = [
        check_missing_citations(tex, find_bib_files(target, bib_files)),
        check_figures(tex, base_dir),
        check_duplicate_sections(tex),
    ]
    if with_chktex:
        results.append(run_chktex(main_tex, chktex_suppress))
    return results


def main():
    ap = argparse.ArgumentParser(description="LaTeX 编译前机械四查（缺失引用/缺图/重复图/重复章节）")
    ap.add_argument("target", help="主 .tex 文件或论文项目目录")
    ap.add_argument("--bib", action="append", default=[], help="显式指定 .bib 文件（可多次；默认自动扫描同目录）")
    ap.add_argument("--chktex", action="store_true", help="追加一轮 chktex 静态检查（需安装 chktex）")
    ap.add_argument("--chktex-suppress", default=",".join(str(i) for i in CHKTEX_DEFAULT_SUPPRESS),
                    help="chktex 抑制的告警 ID，逗号分隔（默认 2,24,13,1）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出结构化问题清单（供 formatter_agent 消费）")
    args = ap.parse_args()

    try:
        suppress = [int(x) for x in re.split(r"[,\s]+", args.chktex_suppress.strip()) if x]
        results = run_checks(args.target, args.bib, args.chktex, suppress)
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(2)

    blocking = [r for r in results if r["severity"] in ("error", "warning")]
    if args.json:
        print(json.dumps({
            "target": args.target,
            "clean": not blocking,
            "results": results,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"目标: {args.target}")
        for r in results:
            mark = {"error": "✗", "warning": "⚠", "clean": "✓", "skipped": "-"}[r["severity"]]
            print(f"\n[{mark}] {r['check']}: {r['severity']}")
            for d in r["detail"]:
                print(f"    {d}")
        if not blocking:
            print("\n四查全部通过，可以进入编译。")
        else:
            print(f"\n共 {sum(len(r['detail']) for r in blocking)} 项待处理。"
                  "把以上清单交给 formatter_agent 修订后重跑本脚本，直到清零再编译。")

    sys.exit(1 if blocking else 0)


if __name__ == "__main__":
    main()
