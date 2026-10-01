#!/usr/bin/env python3
"""
check_pipeline_integrity.py — pipeline 阶段交接物确定性校验（fail-closed 门禁）

校验五个阶段转换点的交接产物，把 prompt 级 enforcement 升级为脚本门禁
（orchestrator 在阶段转换点调用 + CI 挂载；校验不过即退出 1，禁止"带病推进"）：

  literature-corpus <file.md>   Stage 1→2 交接清单：五列表头 + 行完整性（可选校验路径存在）
  issue-ids <file.md>           评审产物 Issue ID 语法：EIC/R1/R2/R3/DA(/IP/EX)-<1..99>
  rr-matrix <file.md>           Schema 11 R&R 矩阵：Author's Claim 与 Verified? 列逐行非空
  failure-modes <file.md>       7-mode AI 研究失败清单：七项全有判定 + 阻断条件判定
  passport <file.json> [--resume-hash H]  Material Passport 哈希链与续跑查找（复用 passport_tool）

判定词表（references/ai_research_failure_modes.md）：
  CLEAR / SUSPECTED / INSUFFICIENT EVIDENCE；OVERRIDDEN 需同行附 ≥10 字理由。
  阻断条件：任一 mode SUSPECTED，或 Mode 1/3/5/6 为 INSUFFICIENT EVIDENCE（未获用户日志不得放行）。

用法（单产物校验，退出码 0=通过 / 1=不通过 / 2=用法错误）：
    python check_pipeline_integrity.py literature-corpus papers/corpus.md --check-paths
    python check_pipeline_integrity.py issue-ids review/roadmap.md
    python check_pipeline_integrity.py rr-matrix review/re_review.md
    python check_pipeline_integrity.py failure-modes integrity/stage25.md
    python check_pipeline_integrity.py passport pipeline_passport.json
"""

import argparse
import json
import os
import re
import sys

import mdtables
import passport_tool

# ---------------------------------------------------------------------------
# Issue ID 语法（references/issue_lifecycle_protocol.md §Grammar）
# ---------------------------------------------------------------------------
PANEL_SOURCES = ("EIC", "R1", "R2", "R3", "DA")
NONPANEL_SOURCES = ("IP", "EX")  # 非 panel 来源：in-pair evaluator / external reviewer
KNOWN_SOURCES = set(PANEL_SOURCES) | set(NONPANEL_SOURCES)
# 来源名交替必须显式列出：[A-Z]{1,3} 类通配匹配不了 R1/R2/R3 这种「字母+数字」来源
KNOWN_ID_RE = re.compile(r"\b(EIC|R[1-3]|DA|IP|EX)-(\d{1,2})\b")
# 疑似但前缀未知的编号（用于警告，如 XX-3）
ANY_ID_RE = re.compile(r"\b([A-Z]{2,4})-(\d{1,2})\b")
# panel 形状但前缀非法（如 R9-0：R 后数字不在 1-3）——静默放过会让改号丢失不可见
MALFORMED_PANEL_RE = re.compile(r"\b(R(?![1-3])\d|EIC|DA|IP|EX)-(\d{1,2})\b")

# ---------------------------------------------------------------------------
# 7-mode 清单（references/ai_research_failure_modes.md）
# ---------------------------------------------------------------------------
MODE_VERDICTS = ("CLEAR", "SUSPECTED", "INSUFFICIENT EVIDENCE")
# 未获用户日志不得静默放行的 mode
EVIDENCE_REQUIRED_MODES = {1, 3, 5, 6}
OVERRIDDEN_RE = re.compile(r"OVERRIDDEN[（(]([^（()）]{10,})[)）]")


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        raise RuntimeError(f"无法读取文件 {path}: {e}")


def _iter_tables(text: str):
    return mdtables.iter_tables(text)


# ---------------------------------------------------------------------------
# literature-corpus（pipeline.md § Stage 1 Output Convention）
# ---------------------------------------------------------------------------
def check_literature_corpus(path: str, check_paths: bool) -> dict:
    text = _read(path)
    errors, warnings = [], []
    tables = list(_iter_tables(text))
    expected_cols = ("#", "标题", "来源", "标识符", "本地路径")
    corpus = None
    for header, rows in tables:
        # 表头命中 2 列以上即视为语料表（缺列时进列检查给出具体缺失项，而非"找不到表"）
        if sum(1 for col in expected_cols if col in header) >= 2:
            corpus = (header, rows)
            break
    if corpus is None:
        return {
            "artifact": "literature-corpus",
            "pass": False,
            "errors": ["未找到 Literature Corpus 表（表头需含：# / 标题 / 来源 / 标识符 / 本地路径，见 pipeline.md § Stage 1 Output Convention）"],
            "warnings": [],
            "stats": {},
        }
    header, rows = corpus
    for col in expected_cols:
        if col not in header:
            errors.append(f"表头缺少必需列：{col}（实际：{header}）")
    if not rows:
        errors.append("Literature Corpus 没有任何数据行（Stage 1 检索无产出时应与用户确认缩小范围，而不是交空清单）")
    downloaded = 0
    for i, row in enumerate(rows, 1):
        if len(row) < len(header):
            errors.append(f"第 {i} 行单元格数不足（{len(row)}/{len(header)}）: {row}")
            continue
        cells = {header[j]: row[j] for j in range(len(header))}
        if not cells.get("标题"):
            errors.append(f"第 {i} 行缺标题")
        if not cells.get("来源"):
            errors.append(f"第 {i} 行缺来源")
        if not cells.get("标识符"):
            warnings.append(f"第 {i} 行缺标识符（DOI/arXiv ID 等），后续引用核验与下载反查会受影响")
        local = (cells.get("本地路径") or "").strip()
        if not local:
            warnings.append(f"第 {i} 行本地路径为空（按交接格式应填路径或「（仅摘要）」占位）")
        elif local.startswith("（") or "仅摘要" in local:
            pass  # 摘要占位，非下载条目
        else:
            downloaded += 1
            if "仅摘要" in (cells.get("来源") or ""):
                warnings.append(f"第 {i} 行来源标注「仅摘要」却填了真实路径，两者矛盾")
            elif check_paths and not os.path.isfile(local):
                errors.append(f"第 {i} 行本地路径不存在: {local}")
    return {
        "artifact": "literature-corpus",
        "pass": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": {"rows": len(rows), "downloaded": downloaded, "abstract_only": len(rows) - downloaded},
    }


# ---------------------------------------------------------------------------
# issue-ids（references/issue_lifecycle_protocol.md §Grammar）
# ---------------------------------------------------------------------------
def check_issue_ids(path: str, require_ids: bool) -> dict:
    text = _read(path)
    errors, warnings = [], []
    valid = []
    known_spans = set()
    for m in KNOWN_ID_RE.finditer(text):
        source, num = m.group(1), int(m.group(2))
        known_spans.add(m.span())
        if not 1 <= num <= 99:
            errors.append(f"Issue ID 越界（1-99）: {source}-{num}")
        else:
            valid.append(f"{source}-{num}")
    for m in ANY_ID_RE.finditer(text):
        if m.span() in known_spans or m.group(1) in KNOWN_SOURCES:
            continue
        warnings.append(f"未知来源前缀的疑似 Issue ID: {m.group(0)}（panel 前缀 EIC/R1/R2/R3/DA，非 panel 前缀 IP/EX）")
    for m in MALFORMED_PANEL_RE.finditer(text):
        if m.span() in known_spans:
            continue
        warnings.append(f"panel 形状但来源前缀非法: {m.group(0)}（R 仅允许 R1/R2/R3；若为笔误请修正，防止改号静默丢失）")
    if not valid:
        msg = "未找到任何合法 Issue ID"
        if require_ids:
            errors.append(msg + "（--require 模式：评审产物必须携带 Issue ID）")
        else:
            warnings.append(msg + "——若该文件不是评审产物可忽略")
    # panel 前缀内编号连续性（R2-1 出现而 R2-2 缺失时提示，防手工改号丢链）
    per_source: dict = {}
    for v in valid:
        src, num = v.rsplit("-", 1)
        per_source.setdefault(src, set()).add(int(num))
    for src, nums in sorted(per_source.items()):
        missing = sorted(set(range(1, max(nums) + 1)) - nums)
        if missing:
            ids = ", ".join(f"{src}-{n}" for n in missing)
            warnings.append(f"{src} 前缀编号不连续，缺失：{ids}"
                            "（允许：合并后编号保留、新 round 起新号；请人工确认非改号丢链）")
    return {
        "artifact": "issue-ids",
        "pass": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": {"valid_ids": len(valid), "per_source": {k: len(v) for k, v in sorted(per_source.items())}},
    }


# ---------------------------------------------------------------------------
# rr-matrix（references/re_review_mode_protocol.md § Priority 1 表头）
# ---------------------------------------------------------------------------
def check_rr_matrix(path: str) -> dict:
    text = _read(path)
    errors, warnings = [], []
    matrix_tables = []
    for header, rows in _iter_tables(text):
        if "Author's Claim" in header and "Verified?" in header:
            matrix_tables.append((header, rows))
    if not matrix_tables:
        return {
            "artifact": "rr-matrix",
            "pass": False,
            "errors": ["未找到 R&R Traceability Matrix 表（表头需含 Author's Claim 与 Verified? 列）"],
            "warnings": [],
            "stats": {},
        }
    total = cannot_verify = 0
    for header, rows in matrix_tables:
        claim_idx = header.index("Author's Claim")
        verified_idx = header.index("Verified?")
        for i, row in enumerate(rows, 1):
            total += 1
            if len(row) <= max(claim_idx, verified_idx):
                errors.append(f"第 {i} 行单元格数不足（{len(row)} 列，表头 {len(header)} 列）")
                continue
            claim = row[claim_idx].strip()
            verified = row[verified_idx].strip()
            if not claim or claim.startswith("["):
                errors.append(f"第 {i} 行 Author's Claim 为空或占位符（审稿意见必须有作者回应主张）")
            if not verified or verified.startswith("["):
                errors.append(f"第 {i} 行 Verified? 为空（每行必须给出核验判定）")
            elif "Cannot verify" in verified:
                cannot_verify += 1
    if cannot_verify:
        warnings.append(f"{cannot_verify} 行标记 Cannot verify（须在 Quality Assessment 中说明，不得静默）")
    return {
        "artifact": "rr-matrix",
        "pass": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": {"rows": total, "cannot_verify": cannot_verify, "tables": len(matrix_tables)},
    }


# ---------------------------------------------------------------------------
# failure-modes（references/ai_research_failure_modes.md）
# ---------------------------------------------------------------------------
MODE_HEADER_RE = re.compile(r"^\s*(?:#+\s*)?(?:\*\*)?(?:M([1-7])|Mode\s*([1-7]))\b", re.IGNORECASE)
# 判定词全大写且有 \b 边界、大小写敏感：正文小写的 "unclear"/"clearly" 不得误判为判定词
# （fail-open 漏洞：无边界 + IGNORECASE 时 "unclear" 会被读成 CLEAR，静默放行阻断门）
VERDICT_RE = re.compile(r"\b(CLEAR|SUSPECTED|INSUFFICIENT\s+EVIDENCE|OVERRIDDEN[（(][^（()）]{10,}[)）])")


def check_failure_modes(path: str, stage: str) -> dict:
    """按行扫描：Mode 标题行开启一个 mode 段，段内首个判定词即该 mode 的判定。

    兼容两种书写：「M1: CLEAR」单行式与「### Mode 1: …」标题 + 后续独立判定行
    （ai_research_failure_modes.md 的实际格式）。段内找不到判定词 = 该 mode 缺判定。
    """
    text = _read(path)
    verdicts: dict = {}
    current = None
    for line in text.split("\n"):
        header = MODE_HEADER_RE.match(line)
        if header:
            current = int(header.group(1) or header.group(2))
            # 标题行内联判定的场景（M1: CLEAR）
            inline = VERDICT_RE.search(line[len(header.group(0)):])
            if inline:
                verdicts[current] = _normalize_verdict(inline.group(1), stage)
                current = None
            continue
        if current is None:
            continue
        m = VERDICT_RE.search(line)
        if m:
            verdicts[current] = _normalize_verdict(m.group(1), stage)
            current = None

    errors, warnings = [], []
    missing = [n for n in range(1, 8) if n not in verdicts]
    if missing:
        ids = ", ".join(f"M{n}" for n in missing)
        errors.append(f"Mode {ids} 缺少判定（七项必须全部给出 CLEAR/SUSPECTED/INSUFFICIENT EVIDENCE）")

    suspected = sorted(n for n, v in verdicts.items() if v == "SUSPECTED")
    insuff = sorted(n for n, v in verdicts.items() if v == "INSUFFICIENT EVIDENCE")
    # 阻断条件 2.5 与 4.5 相同：任一 SUSPECTED 阻断（4.5 额外的"2.5 曾 SUSPECTED 须已解决"
    # 属会话级历史对照，脚本只见单份产物，由 orchestrator 持有的 integrity_history 负责）
    blocked_modes = suspected + [n for n in insuff if n in EVIDENCE_REQUIRED_MODES]
    if blocked_modes:
        ids = ", ".join(f"M{n}" for n in blocked_modes)
        errors.append(
            f"阻断条件命中：{ids} "
            "（任一 SUSPECTED 阻断；M1/3/5/6 INSUFFICIENT EVIDENCE 需用户日志才能排除）。"
            "如属误报，请用户 Override-with-reasoning 并以 OVERRIDDEN(理由) 记录后重跑本检查。"
        )
    for n in insuff:
        if n not in EVIDENCE_REQUIRED_MODES:
            warnings.append(f"M{n} INSUFFICIENT EVIDENCE 可带警告继续，但将在 Stage 4.5 复查")
    return {
        "artifact": "failure-modes",
        "pass": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": {"verdicts": {f"M{n}": verdicts.get(n) for n in sorted(verdicts)}, "stage": stage},
    }


def _normalize_verdict(raw: str, stage: str) -> str:
    upper = re.sub(r"\s+", " ", raw.upper())
    if upper.startswith("OVERRIDDEN"):
        # Override-with-reasoning 等价放行（理由长度已由正则强制 ≥10 字）；4.5 保留原词供人工复查
        return "CLEAR" if stage == "2.5" else "OVERRIDDEN"
    return upper


# ---------------------------------------------------------------------------
# passport（复用 passport_tool 的哈希链实现，避免第二实现）
# ---------------------------------------------------------------------------
def check_passport(path: str, resume_hash: str | None) -> dict:
    errors, warnings = [], []
    try:
        passport_data = passport_tool.load_passport(path)
        passport_tool.validate_chain(passport_data, source=path)
        info = {"boundaries": sum(1 for e in passport_tool.get_ledger(passport_data) if e.get("kind") == "boundary")}
        routing = None
        if resume_hash:
            routing = passport_tool.resume_lookup(passport_data, resume_hash)
    except RuntimeError as e:
        return {"artifact": "passport", "pass": False, "errors": [str(e)], "warnings": [], "stats": {}}
    if routing:
        pending = routing.get("pending_decision")
        if pending:
            warnings.append("该边界携带 pending_decision：必须先向用户呈现选项并记录选择，禁止按 next 字段自动推进")
    return {
        "artifact": "passport",
        "pass": True,
        "errors": errors,
        "warnings": warnings,
        "stats": {**info, "resume_routing": routing},
    }


def main():
    ap = argparse.ArgumentParser(description="pipeline 阶段交接物确定性校验（fail-closed）")
    sub = ap.add_subparsers(dest="command", required=True)

    p1 = sub.add_parser("literature-corpus", help="Stage 1→2 文献清单校验")
    p1.add_argument("file")
    p1.add_argument("--check-paths", action="store_true", help="校验本地路径指向的文件真实存在")

    p2 = sub.add_parser("issue-ids", help="评审产物 Issue ID 语法校验")
    p2.add_argument("file")
    p2.add_argument("--require", action="store_true", help="必须找到 Issue ID（评审产物建议开启）")

    p3 = sub.add_parser("rr-matrix", help="Schema 11 R&R 矩阵完整性校验")
    p3.add_argument("file")

    p4 = sub.add_parser("failure-modes", help="7-mode 失败清单判定完整性 + 阻断条件")
    p4.add_argument("file")
    p4.add_argument("--stage", choices=["2.5", "4.5"], default="2.5", help="所处诚信门禁阶段")

    p5 = sub.add_parser("passport", help="Material Passport 哈希链校验")
    p5.add_argument("file")
    p5.add_argument("--resume-hash", default=None, help="附加校验 resume_from_passport 路由")

    for p in (p1, p2, p3, p4, p5):
        p.add_argument("--json", action="store_true", help="JSON 输出（供 orchestrator 消费）")

    args = ap.parse_args()
    try:
        if args.command == "literature-corpus":
            result = check_literature_corpus(args.file, args.check_paths)
        elif args.command == "issue-ids":
            result = check_issue_ids(args.file, args.require)
        elif args.command == "rr-matrix":
            result = check_rr_matrix(args.file)
        elif args.command == "failure-modes":
            result = check_failure_modes(args.file, args.stage)
        else:
            result = check_passport(args.file, args.resume_hash)
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(2)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        mark = "✓ 通过" if result["pass"] else "✗ 不通过"
        print(f"[{result['artifact']}] {mark}")
        for e in result["errors"]:
            print(f"    错误: {e}")
        for w in result["warnings"]:
            print(f"    警告: {w}")
        if result["stats"]:
            print(f"    统计: {json.dumps(result['stats'], ensure_ascii=False)}")
        if not result["pass"]:
            print("阶段门禁未通过：先修复以上错误再推进（fail-closed，禁止跳过）。")

    sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
