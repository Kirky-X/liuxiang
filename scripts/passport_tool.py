#!/usr/bin/env python3
"""
passport_tool.py — Material Passport 快照工具（emit / validate / resume 查找）

把 reference/pipeline.md 与 references/passport_as_reset_boundary.md 的 prompt 级
passport 协议升级为脚本可验证：
  - emit     向 Schema 9 的 reset_boundary[] 追加一条 kind: boundary 条目，
             按 RFC 8785 (JCS) 规范化序列化后计算 SHA-256 前 12 位作为 hash
  - validate 逐条重算边界哈希链，校验 resume 消费记录与双消费禁令
  - resume   按 hash 定位边界条目，输出续跑路由（next / pending_decision 选项），
             供 orchestrator 核对 resume_from_passport=<hash> 请求

规范化规则（与 passport_as_reset_boundary.md §"Compute hash" 逐条对应，实现即证据）：
  - 每条条目 JSON Canonical Form：UTF-8、无空白、键按 ASCII 升序
  - 条目间以单个 LF 分隔，第一条无前导分隔，最后一条有尾随 LF
  - 新条目以占位 hash "000000000000" 参与哈希，算完覆写
  - 只有 kind: boundary 条目参与哈希（kind: resume 不计入）
  - 哈希 = SHA-256 小写 hex 前 12 位

用法：
    python passport_tool.py emit pipeline_passport.json --stage 3 --next 4 --session-marker sess_xxx
    python passport_tool.py validate pipeline_passport.json
    python passport_tool.py resume pipeline_passport.json <hash>

退出码：0 = 成功/校验通过；1 = 校验失败/哈希不匹配/双消费；2 = 用法错误。
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

PLACEHOLDER_HASH = "000000000000"
LEDGER_KEY = "reset_boundary"
BOUNDARY_KIND = "boundary"
RESUME_KIND = "resume"


def jcs_serialize(obj) -> bytes:
    """RFC 8785 (JCS) 的实用子集实现：UTF-8、紧凑分隔符、键 ASCII 升序。

    本协议的条目只含字符串/数字/布尔/null，不涉及 JCS 的数字规范化边角
    （浮点按 ECMAScript NumberToString 排布）——条目构造时避免写入浮点即可
    保持跨实现一致。ensure_ascii=False 保证非 ASCII 字符按 UTF-8 原样输出。
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_ledger_stream(boundary_entries: list) -> bytes:
    """把边界条目序列化为规范字节流：每条后跟一个 LF（等价于 join LF + 尾 LF）。"""
    return b"".join(jcs_serialize(e) + b"\n" for e in boundary_entries)


def compute_boundary_hash(prior_boundaries: list, new_entry: dict) -> str:
    """对已有边界链 + 新条目（hash 为占位符）计算 12 位哈希。

    kind: resume 条目按规范铁律从不参与边界哈希计算，此处强制过滤，
    保证任何调用方传入混有 resume 的列表都不会算出错误哈希。
    """
    boundaries = [e for e in prior_boundaries if e.get("kind") == BOUNDARY_KIND]
    staged = dict(new_entry)
    staged["hash"] = PLACEHOLDER_HASH
    stream = canonical_ledger_stream(boundaries + [staged])
    return hashlib.sha256(stream).hexdigest()[:12]


def load_passport(path: str, allow_missing: bool = False) -> dict:
    if allow_missing and not (os.path.exists(path) and os.path.getsize(path) > 0):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise RuntimeError(f"无法读取 passport 文件 {path}: {e}")
    except ValueError as e:
        raise RuntimeError(f"passport 文件不是合法 JSON：{path}（{e}）")


def save_passport(path: str, passport: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(passport, f, ensure_ascii=False, indent=2)
        f.write("\n")


def get_ledger(passport: dict) -> list:
    return passport.get(LEDGER_KEY) or []


def validate_chain(passport: dict, source: str = "<passport>") -> list:
    """重算整条边界哈希链并检查 resume 消费记录。失败抛 RuntimeError。"""
    ledger = get_ledger(passport)
    prior_boundaries = []
    consumed = {}  # hash -> resume entry index
    for idx, entry in enumerate(ledger):
        kind = entry.get("kind")
        if kind == BOUNDARY_KIND:
            expected = entry.get("hash")
            if not expected:
                raise RuntimeError(f"{source}: 边界条目 #{idx} 缺少 hash 字段。")
            actual = compute_boundary_hash(prior_boundaries, entry)
            if actual != expected:
                raise RuntimeError(
                    f"{source}: 边界条目 #{idx}（stage={entry.get('stage')}）哈希不匹配："
                    f"记录值 {expected}，重算值 {actual}。条目在写入后被改动过，或序列化不一致。"
                )
            prior_boundaries.append(entry)
        elif kind == RESUME_KIND:
            target = entry.get("consumes_hash")
            known = {b.get("hash") for b in prior_boundaries}
            if target not in known:
                raise RuntimeError(
                    f"{source}: resume 条目 #{idx} 的 consumes_hash={target} "
                    "未匹配到任何先前的边界条目。"
                )
            if target in consumed:
                raise RuntimeError(
                    f"{source}: 边界条目 {target} 被重复消费（resume #{consumed[target]} 与 #{idx}）。"
                    "双消费违反 append-only 续跑协议。"
                )
            consumed[target] = idx
        else:
            raise RuntimeError(f"{source}: 条目 #{idx} 的 kind={kind!r} 非法（只允许 boundary/resume）。")
    return ledger


def resume_lookup(passport: dict, target_hash: str) -> dict:
    """按 hash 定位边界条目并给出续跑路由。失败抛 RuntimeError。"""
    ledger = get_ledger(passport)
    target_idx = None
    for idx, entry in enumerate(ledger):
        if entry.get("kind") == BOUNDARY_KIND and entry.get("hash") == target_hash:
            target_idx = idx
            break
    if target_idx is None:
        known = [e.get("hash") for e in ledger if e.get("kind") == BOUNDARY_KIND]
        raise RuntimeError(
            f"未找到 hash={target_hash} 的边界条目。可用边界：{known or '（无）'}。"
            "哈希不匹配是硬错误，不要猜测或篡改后继续。"
        )
    for entry in ledger[target_idx + 1:]:
        if entry.get("kind") == RESUME_KIND and entry.get("consumes_hash") == target_hash:
            raise RuntimeError(
                f"边界条目 {target_hash} 已被 resume 消费过（会话 {entry.get('session_marker')}）。"
                "同一边界只允许续跑一次；请改用其后的最新边界哈希。"
            )
    boundary = ledger[target_idx]
    pending = boundary.get("pending_decision")
    return {
        "hash": target_hash,
        "stage": boundary.get("stage"),
        "next": boundary.get("next"),
        "version_label": boundary.get("version_label"),
        "session_marker": boundary.get("session_marker"),
        "awaiting_decision": bool(pending),
        "pending_decision": pending,
        "routing": (
            "必须先向用户呈现 pending_decision 选项并记录其选择，"
            "按所选项的 next_stage/next_mode 路由；不得用 next 字段自动推进。"
            if pending
            else f"按边界记录的 next={boundary.get('next')} 进入下一阶段（可用 stage=/mode= 覆盖）。"
        ),
    }


def emit_boundary(path: str, stage, next_stage, session_marker: str | None = None,
                  version_label: str | None = None, pending_decision: dict | None = None) -> dict:
    """向 passport 追加一条边界条目（计算并写入 hash），返回新条目。文件不存在时新建。

    追加前先校验既有哈希链（与 record_resume 对称）：在已损坏的 ledger 上继续
    append 会把新哈希算在被篡改的数据之上，故障点被推远离写入点。
    """
    passport = load_passport(path, allow_missing=True)
    if get_ledger(passport):
        validate_chain(passport, source=path)
    prior = [e for e in get_ledger(passport) if e.get("kind") == BOUNDARY_KIND]
    entry = {
        "kind": BOUNDARY_KIND,
        "stage": stage,
        "next": next_stage,
        "version_label": version_label or f"checkpoint_v{len(prior) + 1}",
        "session_marker": session_marker,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if pending_decision is not None:
        entry["pending_decision"] = pending_decision
    entry["hash"] = compute_boundary_hash(prior, entry)
    passport.setdefault(LEDGER_KEY, []).append(entry)
    save_passport(path, passport)
    return entry


def record_resume(path: str, target_hash: str, session_marker: str | None = None) -> dict:
    """定位边界条目并追加 kind: resume 消费记录（append-only 续跑痕迹）。

    协议要求消费必须留痕——双消费禁令依赖记录存在。重复消费在此被拒绝。
    """
    passport = load_passport(path)
    validate_chain(passport, source=path)
    info = resume_lookup(passport, target_hash)
    entry = {
        "kind": RESUME_KIND,
        "consumes_hash": target_hash,
        "session_marker": session_marker,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    passport.setdefault(LEDGER_KEY, []).append(entry)
    save_passport(path, passport)
    info["consumption_recorded"] = True
    return info


def main():
    ap = argparse.ArgumentParser(description="Material Passport 快照工具（emit/validate/resume）")
    sub = ap.add_subparsers(dest="command", required=True)

    p_emit = sub.add_parser("emit", help="追加一条 kind: boundary 快照条目")
    p_emit.add_argument("passport", help="passport JSON 文件（不存在则创建）")
    p_emit.add_argument("--stage", required=True, help="完成的阶段编号/名称")
    p_emit.add_argument("--next", dest="next_stage", required=True, help="建议的下一阶段")
    p_emit.add_argument("--session-marker", default=None, help="发出会话标识")
    p_emit.add_argument("--version-label", default=None, help="版本标签（默认 checkpoint_vN）")
    p_emit.add_argument("--pending-decision", default=None,
                        help="JSON 文件，含 question 与 options[]（每个选项含 value/next_stage[/next_mode]）")

    p_val = sub.add_parser("validate", help="重算边界哈希链并检查 resume 消费记录")
    p_val.add_argument("passport", help="passport JSON 文件")

    p_res = sub.add_parser("resume", help="按 hash 定位边界条目，追加消费记录并输出续跑路由")
    p_res.add_argument("passport", help="passport JSON 文件")
    p_res.add_argument("hash", help="resume_from_passport= 的 12 位哈希")
    p_res.add_argument("--session-marker", default=None, help="续跑会话标识")

    args = ap.parse_args()
    try:
        if args.command == "emit":
            pending = None
            if args.pending_decision:
                try:
                    with open(args.pending_decision, encoding="utf-8") as f:
                        pending = json.load(f)
                except OSError as e:
                    raise RuntimeError(f"无法读取 pending_decision 文件 {args.pending_decision}: {e}")
                except ValueError as e:
                    raise RuntimeError(f"pending_decision 文件不是合法 JSON：{args.pending_decision}（{e}）")
                if not isinstance(pending, dict) or not pending.get("options"):
                    raise RuntimeError("pending_decision JSON 必须是含 question 与非空 options[] 的对象。")
            entry = emit_boundary(
                args.passport, args.stage, args.next_stage,
                args.session_marker, args.version_label, pending,
            )
            print(f"[PASSPORT-RESET: hash={entry['hash']}, stage={entry['stage']}, next={entry['next']}]")
            print(f"已写入 {args.passport}。跨会话续跑命令：resume_from_passport={entry['hash']}")
        elif args.command == "validate":
            ledger = validate_chain(load_passport(args.passport), source=args.passport)
            boundaries = [e for e in ledger if e.get("kind") == BOUNDARY_KIND]
            consumed = {e.get("consumes_hash") for e in ledger if e.get("kind") == RESUME_KIND}
            awaiting = [b.get("hash") for b in boundaries if b.get("hash") not in consumed]
            print(f"校验通过：{len(boundaries)} 条边界、{len(consumed)} 次消费记录，哈希链完整。")
            print(f"待续跑边界：{awaiting or '（无）'}")
        elif args.command == "resume":
            info = record_resume(args.passport, args.hash, session_marker=args.session_marker)
            print(json.dumps(info, ensure_ascii=False, indent=2))
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
