#!/usr/bin/env python3
"""check_pipeline_integrity.py 离线测试：五类交接物校验（语料表/Issue ID/R&R 矩阵/7-mode/passport）。

全部基于内存/临时文件，不触网。passport 子命令复用 passport_tool，已有其独立测试，
此处只测路由与 pending_decision 警告。
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import check_pipeline_integrity as cpi
import passport_tool as pt

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "check_pipeline_integrity.py")


def write_tmp(content: str, suffix=".md") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


class TestLiteratureCorpus(unittest.TestCase):
    CORPUS = """# Literature Corpus — 测试（2026-10-01）

| # | 标题 | 来源 | 标识符 | 本地路径 |
|---|------|------|--------|----------|
| 1 | Attention Is All You Need | arXiv | 2306.12345 | ./papers/attention.md |
| 2 | 某中文论文 | OpenAlex | DOI:10.xxxx/yy | （仅摘要） |
"""

    def test_valid_corpus_passes(self):
        path = write_tmp(self.CORPUS)
        try:
            result = cpi.check_literature_corpus(path, check_paths=False)
        finally:
            os.unlink(path)
        self.assertTrue(result["pass"], result["errors"])
        self.assertEqual(result["stats"]["rows"], 2)
        self.assertEqual(result["stats"]["downloaded"], 1)

    def test_missing_header_columns(self):
        path = write_tmp("| # | 标题 |\n|---|------|\n| 1 | x |")
        try:
            result = cpi.check_literature_corpus(path, check_paths=False)
        finally:
            os.unlink(path)
        self.assertFalse(result["pass"])
        self.assertTrue(any("缺少必需列" in e for e in result["errors"]))

    def test_empty_corpus_fails(self):
        path = write_tmp("| # | 标题 | 来源 | 标识符 | 本地路径 |\n|---|------|------|--------|----------|")
        try:
            result = cpi.check_literature_corpus(path, check_paths=False)
        finally:
            os.unlink(path)
        self.assertFalse(result["pass"])
        self.assertTrue(any("没有数据行" in e or "没有任何数据行" in e for e in result["errors"]))

    def test_no_table_at_all(self):
        path = write_tmp("不是表格的文档")
        try:
            result = cpi.check_literature_corpus(path, check_paths=False)
        finally:
            os.unlink(path)
        self.assertFalse(result["pass"])

    def test_check_paths_flags_missing_file(self):
        path = write_tmp(self.CORPUS)
        try:
            result = cpi.check_literature_corpus(path, check_paths=True)
        finally:
            os.unlink(path)
        self.assertFalse(result["pass"])
        self.assertTrue(any("./papers/attention.md" in e for e in result["errors"]))

    def test_abstract_only_with_path_contradiction(self):
        path = write_tmp(
            "| # | 标题 | 来源 | 标识符 | 本地路径 |\n|---|------|------|--------|----------|\n"
            "| 1 | x | OpenAlex（仅摘要） | DOI:10.1/a | ./papers/x.md |")
        try:
            result = cpi.check_literature_corpus(path, check_paths=False)
        finally:
            os.unlink(path)
        self.assertTrue(result["pass"])
        self.assertTrue(any("矛盾" in w for w in result["warnings"]))


class TestIssueIds(unittest.TestCase):
    def test_valid_ids(self):
        path = write_tmp("issues: EIC-1, R1-4, R2-3, DA-7, IP-1, EX-2")
        try:
            result = cpi.check_issue_ids(path, require_ids=False)
        finally:
            os.unlink(path)
        self.assertTrue(result["pass"], result["errors"])
        self.assertEqual(result["stats"]["valid_ids"], 6)

    def test_out_of_range_rejected(self):
        # \d{1,2} 语法上封顶两位数，0 是唯一能触发越界检查的输入
        path = write_tmp("R1-0")
        try:
            result = cpi.check_issue_ids(path, require_ids=False)
        finally:
            os.unlink(path)
        self.assertFalse(result["pass"])
        self.assertTrue(any("越界" in e for e in result["errors"]))

    def test_require_mode_fails_empty(self):
        path = write_tmp("没有任何编号的文档")
        try:
            result = cpi.check_issue_ids(path, require_ids=True)
        finally:
            os.unlink(path)
        self.assertFalse(result["pass"])
        self.assertTrue(any("未找到任何合法 Issue ID" in e for e in result["errors"]))

    def test_unknown_prefix_warns(self):
        path = write_tmp("XX-3 应当警告")
        try:
            result = cpi.check_issue_ids(path, require_ids=False)
        finally:
            os.unlink(path)
        self.assertTrue(result["pass"])
        self.assertTrue(any("XX-3" in w for w in result["warnings"]))

    def test_gap_numbering_warns(self):
        path = write_tmp("R2-1 R2-3")
        try:
            result = cpi.check_issue_ids(path, require_ids=False)
        finally:
            os.unlink(path)
        self.assertTrue(result["pass"])
        self.assertTrue(any("R2-2" in w for w in result["warnings"]))


class TestRRMatrix(unittest.TestCase):
    MATRIX = """### Priority 1 — Required Revisions

| # | Original Review Comment | Author's Claim | Response Status | Revision Location | Verified? | Quality Assessment |
|---|------------------------|---------------|-----------------|-------------------|-----------|-------------------|
| R1 | Add ablation | Added Table 5 | FULLY_ADDRESSED | Sec 4.2 | ✅ Yes | OK |
| R2 | Fix typo | Fixed in Sec 2 | FULLY_ADDRESSED | Sec 2.1 | 🔍 Cannot verify | Unrelated claim |
| R3 | More seeds | [addressed as suggested] | PARTIAL | Sec 3 | | gap |
"""

    def test_row_violations_detected(self):
        path = write_tmp(self.MATRIX)
        try:
            result = cpi.check_rr_matrix(path)
        finally:
            os.unlink(path)
        self.assertFalse(result["pass"], result["errors"])
        joined = "\n".join(result["errors"])
        self.assertIn("占位符", joined)
        self.assertIn("Verified? 为空", joined)
        self.assertEqual(result["stats"]["cannot_verify"], 1)
        self.assertEqual(result["stats"]["rows"], 3)

    def test_clean_matrix_passes(self):
        clean = self.MATRIX.replace("[addressed as suggested]", "Re-ran 5 seeds").replace("| PARTIAL | Sec 3 | | gap |", "| PARTIAL | Sec 3 | ⚠️ Partial | gap |")
        self.assertNotIn("[addressed", clean)
        path = write_tmp(clean)
        try:
            result = cpi.check_rr_matrix(path)
        finally:
            os.unlink(path)
        self.assertTrue(result["pass"], result["errors"])

    def test_no_matrix_fails(self):
        path = write_tmp("没有矩阵")
        try:
            result = cpi.check_rr_matrix(path)
        finally:
            os.unlink(path)
        self.assertFalse(result["pass"])


class TestFailureModes(unittest.TestCase):
    FULL_CLEAR = "\n".join(f"### Mode {n}: x\n**判定**: CLEAR" for n in range(1, 8))

    def test_all_clear_passes(self):
        path = write_tmp(self.FULL_CLEAR)
        try:
            result = cpi.check_failure_modes(path, "2.5")
        finally:
            os.unlink(path)
        self.assertTrue(result["pass"], result["errors"])
        self.assertEqual(len(result["stats"]["verdicts"]), 7)

    def test_missing_verdicts_fail(self):
        path = write_tmp("### Mode 1: x\nCLEAR\n### Mode 2: x\nCLEAR")
        try:
            result = cpi.check_failure_modes(path, "2.5")
        finally:
            os.unlink(path)
        self.assertFalse(result["pass"])
        self.assertTrue(any("缺少判定" in e for e in result["errors"]))

    def test_any_suspected_blocks(self):
        text = self.FULL_CLEAR.replace("### Mode 4: x\n**判定**: CLEAR", "### Mode 4: x\n**判定**: SUSPECTED")
        path = write_tmp(text)
        try:
            result = cpi.check_failure_modes(path, "2.5")
        finally:
            os.unlink(path)
        self.assertFalse(result["pass"])
        self.assertTrue(any("M4" in e for e in result["errors"]))

    def test_lowercase_or_embedded_words_are_not_verdicts(self):
        # 架构审查 M1 回归：正文小写 "unclear"/"clearly" 不得被读成判定词（fail-open 漏洞）
        text = "### Mode 1: x\nunclear results were clearly described\n" + "\n".join(
            f"### Mode {n}: x\n**判定**: CLEAR" for n in range(2, 8))
        path = write_tmp(text)
        try:
            result = cpi.check_failure_modes(path, "2.5")
        finally:
            os.unlink(path)
        self.assertFalse(result["pass"])  # M1 无大写判定词 → 缺判定 → fail-closed

    def test_m1356_insufficient_evidence_blocks_but_m247_warns(self):
        blocked = self.FULL_CLEAR.replace("### Mode 5: x\n**判定**: CLEAR", "### Mode 5: x\n**判定**: INSUFFICIENT EVIDENCE")
        path = write_tmp(blocked)
        try:
            r1 = cpi.check_failure_modes(path, "2.5")
        finally:
            os.unlink(path)
        self.assertFalse(r1["pass"])
        warned = self.FULL_CLEAR.replace("### Mode 2: x\n**判定**: CLEAR", "### Mode 2: x\n**判定**: INSUFFICIENT EVIDENCE")
        path = write_tmp(warned)
        try:
            r2 = cpi.check_failure_modes(path, "2.5")
        finally:
            os.unlink(path)
        self.assertTrue(r2["pass"], r2["errors"])
        self.assertTrue(any("4.5 复查" in w for w in r2["warnings"]))

    def test_override_with_reason_clears_at_25(self):
        text = self.FULL_CLEAR.replace(
            "### Mode 3: x\n**判定**: CLEAR",
            "### Mode 3: x\n**判定**: OVERRIDDEN(用户提供了实验日志证明结果真实可复现)")
        path = write_tmp(text)
        try:
            result = cpi.check_failure_modes(path, "2.5")
        finally:
            os.unlink(path)
        self.assertTrue(result["pass"], result["errors"])

    def test_mode_wording_also_accepted(self):
        text = "\n".join(f"Mode {n}: CLEAR" for n in range(1, 8))
        path = write_tmp(text)
        try:
            result = cpi.check_failure_modes(path, "2.5")
        finally:
            os.unlink(path)
        self.assertTrue(result["pass"], result["errors"])


class TestPassportSubcommand(unittest.TestCase):
    def test_valid_passport_with_pending_decision_warning(self):
        entry = {
            "kind": "boundary", "stage": "3", "next": "4",
            "version_label": "checkpoint_v1", "session_marker": "s1",
            "generated_at": "2026-10-01T00:00:00+00:00",
            "pending_decision": {"question": "q", "options": [{"value": "revise", "next_stage": "4"}]},
        }
        entry["hash"] = pt.compute_boundary_hash([], entry)
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({pt.LEDGER_KEY: [entry]}, f, ensure_ascii=False)
        self.addCleanup(os.unlink, path)
        result = cpi.check_passport(path, resume_hash=entry["hash"])
        self.assertTrue(result["pass"], result["errors"])
        self.assertTrue(any("pending_decision" in w for w in result["warnings"]))

    def test_tampered_passport_fails(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({pt.LEDGER_KEY: [{"kind": "boundary", "hash": "aaaaaaaaaaaa"}]}, f)
        self.addCleanup(os.unlink, path)
        result = cpi.check_passport(path, resume_hash=None)
        self.assertFalse(result["pass"])


class TestCliSmoke(unittest.TestCase):
    def test_literature_corpus_exit_codes(self):
        good = write_tmp(self.CORPUS if hasattr(self, "CORPUS") else TestLiteratureCorpus.CORPUS)
        try:
            r = subprocess.run([sys.executable, "-B", SCRIPT, "literature-corpus", good],
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0)
            r = subprocess.run([sys.executable, "-B", SCRIPT, "literature-corpus", good, "--json"],
                               capture_output=True, text=True, timeout=60)
            self.assertIn('"pass": true', r.stdout)
        finally:
            os.unlink(good)

    def test_bad_file_exit_2(self):
        r = subprocess.run([sys.executable, "-B", SCRIPT, "issue-ids", "/nonexistent.md"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
