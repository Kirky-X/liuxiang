#!/usr/bin/env python3
"""check_inventory.py 离线测试：以合成 fixture 根目录验证对账引擎（数字声明/列表声明/自洽检查）。"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import check_inventory as ci

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "check_inventory.py")

AGENTS = [f"{m}_agent.md" for m in (
    ["intake", "literature_strategist", "structure_architect", "argument_builder", "draft_writer",
     "citation_compliance", "abstract_bilingual", "peer_reviewer", "formatter", "revision_coach",
     "socratic_mentor", "visualization"]
    + ["field_analyst", "eic", "methodology_reviewer", "domain_reviewer", "perspective_reviewer",
       "devils_advocate_reviewer", "editorial_synthesizer"]
    + ["pipeline_orchestrator", "state_tracker", "integrity_verification", "collaboration_depth",
       "claim_ref_alignment_audit"])]


def build_fixture(tmp: str, *, paper_modes=10, claimed_modes=10, sources=("openalex", "crossref")):
    os.makedirs(os.path.join(tmp, "agents"))
    for fn in AGENTS:
        open(os.path.join(tmp, "agents", fn), "w").close()
    os.makedirs(os.path.join(tmp, "reference"))
    os.makedirs(os.path.join(tmp, "references"))
    os.makedirs(os.path.join(tmp, "scripts"))

    paper_rows = "\n".join(f"| {i+1} | `agent{i}` | R | P{i} |" for i in range(12))
    open(os.path.join(tmp, "reference", "paper.md"), "w", encoding="utf-8").write(
        f"## Agent Team\n\n| # | Agent | Role | Phase |\n|---|---|---|---|\n{paper_rows}\n\n"
        "## Operational Modes\n\n"
        + "\n".join(f"| `{m}` | T | A | O |" for m in list(_MODE_NAMES)[:paper_modes]) + "\n\n"
        "### Citation Formats\n\nAPA 7.0 (default), Chicago, MLA 9, IEEE, Vancouver.\n")
    reviewer_rows = "\n".join(f"| {i+1} | `ragent{i}` | R | P |" for i in range(7))
    open(os.path.join(tmp, "reference", "reviewer.md"), "w", encoding="utf-8").write(
        "## Agent Team\n\n| # | Agent | Role | Phase |\n|---|---|---|---|\n"
        + reviewer_rows + "\n\n## Operational Modes\n\n"
        + "\n".join("| `%s` | T | A | O |" % m for m in _REVIEWER_MODES) + "\n")
    open(os.path.join(tmp, "reference", "pipeline.md"), "w", encoding="utf-8").write(
        "## Agent Team\n\n| # | Agent | Role | Phase |\n|---|---|---|---|\n"
        + "\n".join(f"| {i+1} | `pag{i}` | R | P |" for i in range(5))
        + "\n\n## Pipeline Stages (10 Stages)\n\n| Stage | Name |\n|---|---|\n"
        + "\n".join(f"| **{s}** | X |" for s in ["1", "2", "2.5", "3", "4", "3'", "4'", "4.5", "5", "6"]) + "\n")
    patterns = "\n".join(f"## Pattern {i}: T{i}" for i in range(1, 7))
    open(os.path.join(tmp, "references", "paper_structure_patterns.md"), "w", encoding="utf-8").write(patterns + "\n")

    choices = ", ".join(f'"{s}"' for s in ["auto", "multi", *sources])
    open(os.path.join(tmp, "scripts", "search_papers.py"), "w", encoding="utf-8").write(
        f'ap.add_argument("--source", choices=[{choices}], default="auto")\n')

    mode_list = " / ".join(_SHORT.get(m, m) for m in list(_MODE_NAMES)[:paper_modes])
    src_list = " / ".join(_SRC_DISPLAY.get(s, s) for s in sources)
    open(os.path.join(tmp, "SKILL.md"), "w", encoding="utf-8").write(
        f"12-agent 论文写作，{claimed_modes} 模式，6 论文类型，5 引用格式。\n"
        f"7-agent 多视角同行评审，6 模式。\n端到端 10 阶段流水线。\n"
        f"论文写作（{'/'.join(_SHORT.get(m, m) for m in list(_MODE_NAMES)[:paper_modes])}）\n"
        f"脚本驱动（{src_list} 多源）\n")
    open(os.path.join(tmp, "README.md"), "w", encoding="utf-8").write(
        f"| search | x | {len(sources)} 个数据源：{src_list} |\n"
        f"| paper | 12-agent 论文写作 | {claimed_modes} 种模式（...）、6 论文类型、5 引用格式 |\n"
        f"| reviewer | 7-agent 多视角同行评审 | 6 种模式（...） |\n"
        f"| pipeline | 端到端 10 阶段流水线 | ... |\n"
        f"agents/ 共 24 个 agent\n")
    open(os.path.join(tmp, "README_EN.md"), "w", encoding="utf-8").write(
        f"| search | x | {len(sources)} sources: {src_list} |\n"
        f"| paper | 12-agent paper writing | {claimed_modes} modes (...), 6 paper types, 5 citation formats |\n"
        f"| reviewer | 7-agent multi-perspective peer review | 6 modes (...) |\n"
        f"| pipeline | End-to-end 10-stage pipeline | ... |\n")


_MODE_NAMES = ["full", "outline-only", "revision", "abstract-only", "lit-review",
               "format-convert", "citation-check", "plan", "revision-coach", "disclosure"]
_REVIEWER_MODES = ["full", "re-review", "quick", "methodology-focus", "guided", "calibration"]
_SHORT = {"outline-only": "outline", "abstract-only": "abstract"}
_SRC_DISPLAY = {"openalex": "OpenAlex", "crossref": "Crossref", "semanticscholar": "Semantic Scholar"}


class TestInventoryEngine(unittest.TestCase):
    def make_root(self, **kw):
        tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        build_fixture(tmp, **kw)
        return tmp

    def test_consistent_fixture_passes(self):
        root = self.make_root(paper_modes=10, claimed_modes=10)
        result = ci.run_checks(root)
        self.assertTrue(result["pass"], result["errors"])
        self.assertEqual(result["truth"]["paper_agents"], 12)
        self.assertEqual(result["truth"]["reviewer_agents"], 7)
        self.assertEqual(result["truth"]["agents_total"], 24)
        self.assertEqual(result["truth"]["paper_modes"], 10)
        self.assertEqual(result["truth"]["pipeline_stages"], 10)
        self.assertEqual(result["truth"]["paper_types"], 6)
        self.assertEqual(result["truth"]["citation_formats"], 5)

    def test_claim_drift_detected(self):
        root = self.make_root(claimed_modes=9)
        result = ci.run_checks(root)
        self.assertFalse(result["pass"])
        self.assertTrue(any("9" in e and "10" in e for e in result["errors"]), result["errors"])

    def test_missing_claim_detected(self):
        root = self.make_root()
        path = os.path.join(root, "README.md")
        text = open(path, encoding="utf-8").read().replace("agents/ 共 24 个 agent\n", "")
        open(path, "w", encoding="utf-8").write(text)
        result = ci.run_checks(root)
        self.assertFalse(result["pass"])
        self.assertTrue(any("未找到声明" in e for e in result["errors"]))

    def test_missing_source_in_list_detected(self):
        root = self.make_root(sources=("openalex", "crossref"))
        # 磁盘加了第三个源但文档清单没更新 → 模拟文档漏列漂移
        sp = os.path.join(root, "scripts", "search_papers.py")
        with open(sp, "w", encoding="utf-8") as f:
            f.write('ap.add_argument("--source", choices=["auto", "multi", "openalex", "crossref", "openaire"], default="auto")\n')
        result = ci.run_checks(root)
        self.assertFalse(result["pass"])
        self.assertTrue(any("openaire" in e for e in result["errors"]), result["errors"])

    def test_agent_table_sum_mismatch(self):
        root = self.make_root()
        # 磁盘多出一个未登记进任何 Agent Team 表的 agent 文件 → 合计自洽检查必须失败
        with open(os.path.join(root, "agents", "rogue_agent.md"), "w") as f:
            f.write("---\nname: rogue\n---\n")
        result = ci.run_checks(root)
        self.assertFalse(result["pass"])
        self.assertTrue(any("合计" in e for e in result["errors"]), result["errors"])

    def test_cli_exit_codes(self):
        good = self.make_root()
        r = subprocess.run([sys.executable, "-B", SCRIPT, "--root", good],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        bad = self.make_root(claimed_modes=8)
        r = subprocess.run([sys.executable, "-B", SCRIPT, "--root", bad],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 1)
        r = subprocess.run([sys.executable, "-B", SCRIPT, "--root", bad, "--json"],
                           capture_output=True, text=True, timeout=60)
        data = json.loads(r.stdout)
        self.assertFalse(data["pass"])


if __name__ == "__main__":
    unittest.main()
