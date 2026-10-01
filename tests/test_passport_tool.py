#!/usr/bin/env python3
"""passport_tool.py 离线测试：JCS 序列化、边界哈希链、resume 定位与双消费禁令 + CLI 冒烟。

按 references/passport_as_reset_boundary.md 的哈希规范逐条验证。
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import passport_tool as pt

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "passport_tool.py")


def make_entry(stage, next_stage, extra=None):
    entry = {
        "kind": "boundary",
        "stage": stage,
        "next": next_stage,
        "version_label": f"checkpoint_v{stage}",
        "session_marker": "sess_test",
        "generated_at": "2026-10-01T00:00:00+00:00",
    }
    if extra:
        entry.update(extra)
    return entry


class TestCanonicalForm(unittest.TestCase):
    def test_sorted_keys_compact_utf8(self):
        raw = pt.jcs_serialize({"b": 1, "a": "中"})
        self.assertEqual(raw.decode("utf-8"), '{"a":"中","b":1}')
        self.assertIsInstance(raw, bytes)

    def test_trailing_lf_per_entry(self):
        stream = pt.canonical_ledger_stream([{"a": 1}, {"a": 2}])
        self.assertEqual(stream, b'{"a":1}\n{"a":2}\n')


class TestHashChain(unittest.TestCase):
    def test_placeholder_never_in_output(self):
        h = pt.compute_boundary_hash([], make_entry(2, 3))
        self.assertEqual(len(h), 12)
        self.assertNotIn("000000", h)

    def test_hash_depends_on_prior_chain(self):
        e1 = dict(make_entry(1, 2), hash="0" * 12)
        h_alone = pt.compute_boundary_hash([], make_entry(2, 3))
        h_after = pt.compute_boundary_hash([e1], make_entry(2, 3))
        self.assertNotEqual(h_alone, h_after)

    def test_resume_entries_excluded_from_chain(self):
        e1 = dict(make_entry(1, 2), hash="0" * 12)
        resume = {"kind": "resume", "consumes_hash": "0" * 12, "session_marker": "s2"}
        h_with = pt.compute_boundary_hash([e1, resume], make_entry(2, 3))
        h_without = pt.compute_boundary_hash([e1], make_entry(2, 3))
        self.assertEqual(h_with, h_without)

    def test_any_field_change_changes_hash(self):
        base = make_entry(2, 3)
        changed = make_entry(2, 4)
        self.assertNotEqual(pt.compute_boundary_hash([], base), pt.compute_boundary_hash([], changed))

    def test_deterministic_across_key_order(self):
        a = {"kind": "boundary", "stage": "2", "next": "3", "hash": "000000000000"}
        b = {"next": "3", "hash": "000000000000", "kind": "boundary", "stage": "2"}
        self.assertEqual(
            pt.compute_boundary_hash([], a), pt.compute_boundary_hash([], b)
        )


class TestValidateChain(unittest.TestCase):
    def build_passport(self, entries):
        return {pt.LEDGER_KEY: entries}

    def test_valid_chain_passes(self):
        e1 = dict(make_entry(1, 2), hash=pt.compute_boundary_hash([], make_entry(1, 2)))
        e2 = dict(make_entry(2, 3), hash=pt.compute_boundary_hash([e1], make_entry(2, 3)))
        ledger = pt.validate_chain(self.build_passport([e1, e2]))
        self.assertEqual(len(ledger), 2)

    def test_tampered_entry_detected(self):
        e1 = dict(make_entry(1, 2), hash=pt.compute_boundary_hash([], make_entry(1, 2)))
        e2 = dict(make_entry(2, 3), hash=pt.compute_boundary_hash([e1], make_entry(2, 3)))
        e2["next"] = "9"  # 篡改
        with self.assertRaisesRegex(RuntimeError, "哈希不匹配"):
            pt.validate_chain(self.build_passport([e1, e2]))

    def test_resume_of_unknown_hash_rejected(self):
        e1 = dict(make_entry(1, 2), hash=pt.compute_boundary_hash([], make_entry(1, 2)))
        forged = {"kind": "resume", "consumes_hash": "ffffffffffff", "session_marker": "s"}
        with self.assertRaisesRegex(RuntimeError, "consumes_hash"):
            pt.validate_chain(self.build_passport([e1, forged]))

    def test_double_resume_rejected(self):
        e1 = dict(make_entry(1, 2), hash=pt.compute_boundary_hash([], make_entry(1, 2)))
        r1 = {"kind": "resume", "consumes_hash": e1["hash"], "session_marker": "s1"}
        r2 = {"kind": "resume", "consumes_hash": e1["hash"], "session_marker": "s2"}
        with self.assertRaisesRegex(RuntimeError, "重复消费"):
            pt.validate_chain(self.build_passport([e1, r1, r2]))

    def test_illegal_kind_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "kind"):
            pt.validate_chain(self.build_passport([{"kind": "weird"}]))


class TestResumeLookup(unittest.TestCase):
    def make_passport_with_boundary(self, pending=None):
        entry = make_entry(3, 4, extra={"pending_decision": pending} if pending else None)
        entry["hash"] = pt.compute_boundary_hash([], entry)
        return self.build_tmp({pt.LEDGER_KEY: [entry]}), entry["hash"]

    def build_tmp(self, passport):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(passport, f, ensure_ascii=False)
        self.addCleanup(os.unlink, path)
        return path

    def test_found_and_routing(self):
        path, h = self.make_passport_with_boundary()
        info = pt.resume_lookup(pt.load_passport(path), h)
        self.assertEqual(info["stage"], 3)
        self.assertEqual(info["next"], 4)
        self.assertFalse(info["awaiting_decision"])
        self.assertIn("next=4", info["routing"])

    def test_pending_decision_blocks_auto_advance(self):
        pending = {
            "question": "Stage 3 decision?",
            "options": [
                {"value": "revise", "next_stage": "4"},
                {"value": "abort", "next_stage": None},
            ],
        }
        path, h = self.make_passport_with_boundary(pending)
        info = pt.resume_lookup(pt.load_passport(path), h)
        self.assertTrue(info["awaiting_decision"])
        self.assertIn("不得用 next 字段自动推进", info["routing"])

    def test_unknown_hash_is_hard_error(self):
        path, _ = self.make_passport_with_boundary()
        with self.assertRaisesRegex(RuntimeError, "未找到 hash"):
            pt.resume_lookup(pt.load_passport(path), "aaaaaaaaaaaa")


class TestEmit(unittest.TestCase):
    def test_emit_appends_and_validates(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        self.addCleanup(os.unlink, path)
        e1 = pt.emit_boundary(path, "2", "2.5", session_marker="s1")
        e2 = pt.emit_boundary(path, "2.5", "3", session_marker="s1")
        passport = pt.load_passport(path)
        pt.validate_chain(passport)  # 不抛即通过
        self.assertNotEqual(e1["hash"], e2["hash"])
        # e2 的哈希按规范基于「已带最终哈希的 e1」重算，须逐字节一致
        self.assertEqual(e2["hash"], pt.compute_boundary_hash([e1], e2))


class TestEmitValidatesExistingChain(unittest.TestCase):
    def test_emit_on_tampered_ledger_rejected(self):
        # 架构审查 M2 回归：损坏的 ledger 上 emit 必须拒绝（与 record_resume 对称）
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({pt.LEDGER_KEY: [dict(make_entry(1, 2), hash="aaaaaaaaaaaa")]}, f)
        self.addCleanup(os.unlink, path)
        with self.assertRaisesRegex(RuntimeError, "哈希不匹配"):
            pt.emit_boundary(path, "2", "3")

    def test_emit_on_fresh_file_still_works(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        self.addCleanup(os.unlink, path)
        entry = pt.emit_boundary(path, "1", "2")
        self.assertEqual(len(entry["hash"]), 12)


class TestCli(unittest.TestCase):
    def test_emit_validate_resume_roundtrip(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        self.addCleanup(os.unlink, path)
        env = dict(os.environ)
        r1 = subprocess.run(
            [sys.executable, "-B", SCRIPT, "emit", path, "--stage", "2", "--next", "2.5"],
            capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(r1.returncode, 0, r1.stderr)
        h = json.loads(json.dumps(r1.stdout.split("hash=")[1].split(",")[0]))
        r2 = subprocess.run(
            [sys.executable, "-B", SCRIPT, "validate", path],
            capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(r2.returncode, 0, r2.stderr)
        r3 = subprocess.run(
            [sys.executable, "-B", SCRIPT, "resume", path, h],
            capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(r3.returncode, 0, r3.stderr)
        self.assertIn('"stage": "2"', r3.stdout)
        # 二次 resume 同一哈希 → 硬错误退出 1
        r4 = subprocess.run(
            [sys.executable, "-B", SCRIPT, "emit", path, "--stage", "2.5", "--next", "3"],
            capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(r4.returncode, 0, r4.stderr)
        r5 = subprocess.run(
            [sys.executable, "-B", SCRIPT, "resume", path, h],
            capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(r5.returncode, 1)
        # 但 resume 新哈希可行
        h2 = r4.stdout.split("hash=")[1].split(",")[0]
        r6 = subprocess.run(
            [sys.executable, "-B", SCRIPT, "resume", path, h2],
            capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(r6.returncode, 0, r6.stderr)

    def test_validate_tampered_fails(self):
        passport = {pt.LEDGER_KEY: [dict(make_entry(1, 2), hash="aaaaaaaaaaaa")]}
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(passport, f)
        self.addCleanup(os.unlink, path)
        r = subprocess.run(
            [sys.executable, "-B", SCRIPT, "validate", path],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 1)
        self.assertIn("哈希不匹配", r.stderr)


if __name__ == "__main__":
    unittest.main()
