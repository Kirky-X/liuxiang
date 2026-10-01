#!/usr/bin/env python3
"""
test_claim_audit_calibration.py — claim-faithfulness audit 校准工具（v3.8 #103）

实现 references/claim_audit_calibration_protocol.md 的完整 runner 契约：
  validate_gold_set   四条 ingestion 规则 (a)-(d)，违规抛 GoldSetValidationError（含条目序号与规则名）
  run_calibration     Phase 1 judge 调用 → Phase 2 混淆矩阵（aggregate + per-class one-vs-rest）
                      → Phase 3 阈值门 → Phase 4 规范报告形状
  perfect_judge       完美判官桩（回显期望判定），让 T-C1/T-C2/T-C3 无需真实 LLM 即可端到端跑通；
                      生产部署时以真实 judge_fn 替换本桩

T-C1：阈值门（FNR<0.15 AND FPR<0.10）；T-C2：per-class FNR/FPR 报告形状；
T-C3：金标集形状完整性（20 条 = 12 alignment + 8 constraint，validate 干净通过）。

运行：
    python3 -m unittest scripts.test_claim_audit_calibration -v
    python3 -m pytest scripts/test_claim_audit_calibration.py -q
"""

import json
import os
import re
import unittest

GOLD_SET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "fixtures", "claim_audit_calibration", "gold_set.json")

DEFAULT_THRESHOLDS = {"FNR": 0.15, "FPR": 0.10}

ALIGNMENT_JUDGMENTS = ("SUPPORTED", "UNSUPPORTED", "AMBIGUOUS", "RETRIEVAL_FAILED")
CONSTRAINT_JUDGMENTS = ("VIOLATED", "NOT_VIOLATED")
CONSTRAINT_ONLY_FIELDS = ("constraint_under_test_id", "constraint_under_test_rule_text", "manifest_fixture_path")

PER_CLASS_ALIGNMENT = ("SUPPORTED", "UNSUPPORTED", "AMBIGUOUS")


class GoldSetValidationError(RuntimeError):
    """金标集不满足 ingestion 规则；消息含违规条目序号与规则名。按协议不捕获——修金标集。"""


def _derive_constraint_scope(constraint_id: str) -> str:
    """MNC-N → MNC；NC-CN-M → NC；其余形状报错（R2 codex P1：拒绝静默空规则）。"""
    if constraint_id.startswith("MNC-"):
        return "MNC"
    if constraint_id.startswith("NC-CN-"):
        return "NC"
    raise RuntimeError(
        f"constraint_under_test_id 形状非法：{constraint_id!r}（期望 MNC-N 或 NC-CN-M）。"
    )


def validate_gold_set(tuples: list) -> None:
    """协议 §7.7 规则 (a)-(d)，首次违规即抛 GoldSetValidationError。"""
    not_violated = 0
    for i, t in enumerate(tuples):
        kind = t.get("tuple_kind")
        # (d) tuple_kind 合法性
        if kind not in ("alignment", "constraint"):
            raise GoldSetValidationError(f"条目 #{i}：tuple_kind={kind!r} 非法（规则 d），只允许 alignment/constraint。")
        # (a) alignment 判定词覆盖
        if kind == "alignment":
            if t.get("expected_judgment") not in ALIGNMENT_JUDGMENTS:
                raise GoldSetValidationError(
                    f"条目 #{i}：alignment 判定词 {t.get('expected_judgment')!r} 非法（规则 a），"
                    f"只允许 {'/'.join(ALIGNMENT_JUDGMENTS)}。"
                )
        # (b) alignment 条目不得携带 constraint 专有字段
            if any(f in t for f in CONSTRAINT_ONLY_FIELDS):
                raise GoldSetValidationError(
                    f"条目 #{i}：alignment 条目携带 constraint 专有字段（规则 b），"
                    "会污染 per-class 混淆矩阵——两类的 judge 调用形状不同。"
                )
        else:
            # (c) constraint 条目必须有 id + 规则文本或 manifest 路径之一
            cid = t.get("constraint_under_test_id")
            if not cid:
                raise GoldSetValidationError(f"条目 #{i}：constraint 条目缺 constraint_under_test_id（规则 c）。")
            _derive_constraint_scope(cid)  # 形状校验
            has_inline = bool(t.get("constraint_under_test_rule_text"))
            has_manifest = bool(t.get("manifest_fixture_path"))
            if has_inline and has_manifest:
                raise GoldSetValidationError(f"条目 #{i}：规则文本与 manifest 路径只能二选一（规则 c）。")
            if not has_inline and not has_manifest:
                raise GoldSetValidationError(
                    f"条目 #{i}：constraint 条目需要 constraint_under_test_rule_text 或 manifest_fixture_path 之一（规则 c）。"
                )
            if t.get("expected_judgment") not in CONSTRAINT_JUDGMENTS:
                raise GoldSetValidationError(
                    f"条目 #{i}：constraint 判定词 {t.get('expected_judgment')!r} 非法（规则 a/c），"
                    f"只允许 {'/'.join(CONSTRAINT_JUDGMENTS)}。"
                )
            if t.get("expected_judgment") == "NOT_VIOLATED":
                not_violated += 1
    # (d) ≥3 NOT_VIOLATED 下限：防「全 VIOLATED」金标把判官训练成一律拒绝
    if not_violated < 3:
        raise GoldSetValidationError(f"NOT_VIOLATED 条目仅 {not_violated} 条（规则 d），下限 3 条。")


def perfect_judge(claim_text, retrieved_excerpt, anchor_kind, anchor_value,
                  active_constraints, judge_model=None):
    """完美判官桩（与金标 fixture 成对交付，让 T-C1/2/3 无需真实 LLM 即可端到端跑通）。

    桩按确定性规则判定，fixture 的构造保证这些规则在金标上零误差：
      1. active_constraints 非空 → 违规标记词（未提供/未报告/省略/缺失/未按）判 VIOLATED，
         合规标记词（提供/符合/明确列出/附有）判 NOT_VIOLATED
      2. excerpt 为空 → RETRIEVAL_FAILED
      3. claim 的英文关键词命中 excerpt：excerpt 含对冲词（may/might/possibly/unclear）→ AMBIGUOUS，
         否则 SUPPORTED；未命中 → UNSUPPORTED
    生产部署用真实 judge_fn 替换本桩。
    """
    if active_constraints:
        violated_markers = ("未提供", "未报告", "省略", "缺失", "未按", "未说明", "未附")
        compliant_markers = ("提供", "符合", "明确列出", "附有")
        if any(m in claim_text for m in violated_markers):
            return "VIOLATED"
        if any(m in claim_text for m in compliant_markers):
            return "NOT_VIOLATED"
        raise RuntimeError(f"判官桩无法判定该 constraint claim（fixture 需含违规/合规标记词）: {claim_text!r}")
    if retrieved_excerpt is None:
        return "RETRIEVAL_FAILED"
    keywords = [w for w in re.sub(r"[^\w\s]", " ", claim_text).split() if len(w) >= 2
                and re.search(r"[A-Za-z0-9]", w)]
    hedges = ("may", "might", "possibly", "unclear")
    if not any(w.lower() in retrieved_excerpt.lower() for w in keywords):
        return "UNSUPPORTED"
    if any(h in retrieved_excerpt.lower() for h in hedges):
        return "AMBIGUOUS"
    return "SUPPORTED"


def run_calibration(tuples: list, judge_fn, thresholds: dict | None = None) -> dict:
    """协议 Phase 1-4：judge 逐条调用 → 混淆矩阵 → 阈值门 → 规范报告。

    aggregate：任一 mismatch 对期望类计 FN、对错选类计 FP，聚合下 FNR/FPR 对称（协议 §Phase 2）。
    per-class one-vs-rest：RETRIEVAL_FAILED 有意不进 per_class——流水线在判官之前就已
    设定该标签，对判官质量无信息量；但条目仍照常传给 judge_fn（不预过滤，协议明文）。
    """
    validate_gold_set(tuples)
    thresholds = thresholds or DEFAULT_THRESHOLDS

    def invoke(t):
        if t["tuple_kind"] == "alignment":
            retrieved, constraints = t.get("ref_text_excerpt"), []
        else:
            retrieved = t.get("ref_text_excerpt")
            constraints = [{
                "constraint_id": t["constraint_under_test_id"],
                "rule": t.get("constraint_under_test_rule_text"),
                "scope": _derive_constraint_scope(t["constraint_under_test_id"]),
            }]
        return judge_fn(
            claim_text=t["claim_text"], retrieved_excerpt=retrieved,
            anchor_kind=t["anchor"]["kind"], anchor_value=t["anchor"]["value"],
            active_constraints=constraints, judge_model=None,
        )

    actuals = [invoke(t) for t in tuples]
    n_alignment = sum(1 for t in tuples if t["tuple_kind"] == "alignment")
    n_constraint = len(tuples) - n_alignment

    mismatches = sum(1 for t, a in zip(tuples, actuals) if a != t["expected_judgment"])

    def rate(fn, n_pos):
        return round(fn / n_pos, 4) if n_pos else 0.0

    per_class = {k: {"fn": 0, "fp": 0, "n_pos": 0, "n_neg": 0}
                 for k in (*PER_CLASS_ALIGNMENT, "violated_constraint")}
    eligible = sum(1 for t in tuples
                   if t["tuple_kind"] == "constraint" or t["expected_judgment"] != "RETRIEVAL_FAILED")
    for t, actual in zip(tuples, actuals):
        expected = t["expected_judgment"]
        if t["tuple_kind"] == "constraint":
            stats = per_class["violated_constraint"]
            if expected == "VIOLATED":
                stats["n_pos"] += 1
                if actual != "VIOLATED":
                    stats["fn"] += 1
            else:
                stats["n_neg"] += 1
                if actual == "VIOLATED":
                    stats["fp"] += 1
            continue
        if expected == "RETRIEVAL_FAILED":
            continue
        stats = per_class[expected]
        stats["n_pos"] += 1
        if actual != expected:
            stats["fn"] += 1
            # 错选进的其他 alignment 类计 FP
            if actual in per_class and actual != "RETRIEVAL_FAILED":
                per_class[actual]["fp"] += 1
    # alignment 各类的 n_negative = 排除 RETRIEVAL_FAILED 后的非本类条目数
    for k in PER_CLASS_ALIGNMENT:
        per_class[k]["n_neg"] = eligible - per_class[k]["n_pos"]

    report = {
        "FNR": rate(mismatches, len(tuples)),
        "FPR": rate(mismatches, len(tuples)),
        "per_class": {
            k: {
                "FNR": rate(v["fn"], v["n_pos"]),
                "FPR": rate(v["fp"], v["n_neg"]),
                "n_positive": v["n_pos"],
                "n_negative": v["n_neg"],
            }
            for k, v in per_class.items()
        },
        "thresholds": dict(thresholds),
        "n_total": len(tuples),
        "n_alignment": n_alignment,
        "n_constraint": n_constraint,
    }
    return report


def load_gold_set(path: str | None = None) -> list:
    with open(path or GOLD_SET_PATH, encoding="utf-8") as f:
        doc = json.load(f)
    return doc["tuples"]


class CalibrationContractTests(unittest.TestCase):
    """T-C1 / T-C2 / T-C3：校准工具契约（协议 §7.7 + §9）。"""

    @classmethod
    def setUpClass(cls):
        cls.tuples = load_gold_set()

    def test_tc3_gold_set_shape(self):
        """T-C3：金标形状完整——validate 干净通过，计数 12 alignment + 8 constraint。"""
        validate_gold_set(self.tuples)  # 不抛即通过
        alignment = sum(1 for t in self.tuples if t["tuple_kind"] == "alignment")
        constraint = sum(1 for t in self.tuples if t["tuple_kind"] == "constraint")
        self.assertEqual((alignment, constraint), (12, 8))
        self.assertEqual(len(self.tuples), 20)

    def test_tc1_threshold_gates_pass_with_perfect_judge(self):
        """T-C1：完美判官下 FNR<0.15 且 FPR<0.10。"""
        report = run_calibration(self.tuples, perfect_judge)
        self.assertLess(report["FNR"], report["thresholds"]["FNR"],
                        f"T-C1 FNR 门失败：{report['FNR']}")
        self.assertLess(report["FPR"], report["thresholds"]["FPR"],
                        f"T-C1 FPR 门失败：{report['FPR']}")

    def test_tc2_per_class_report_shape(self):
        """T-C2：per-class FNR/FPR + n_positive/n_negative 形状（RETRIEVAL_FAILED 不在 per_class）。"""
        report = run_calibration(self.tuples, perfect_judge)
        self.assertEqual(set(report["per_class"].keys()),
                         {"SUPPORTED", "UNSUPPORTED", "AMBIGUOUS", "violated_constraint"})
        for k, v in report["per_class"].items():
            self.assertIn("FNR", v)
            self.assertIn("FPR", v)
            self.assertIn("n_positive", v)
            self.assertIn("n_negative", v)
            self.assertGreater(v["n_positive"], 0, f"{k} 的 n_positive=0 无法与「未覆盖」区分")
        self.assertEqual(report["n_total"], 20)
        self.assertEqual(report["thresholds"], {"FNR": 0.15, "FPR": 0.10})

    def test_constraint_scope_derivation(self):
        self.assertEqual(_derive_constraint_scope("MNC-1"), "MNC")
        self.assertEqual(_derive_constraint_scope("NC-CN-2"), "NC")
        with self.assertRaisesRegex(RuntimeError, "形状非法"):
            _derive_constraint_scope("XYZ-9")


class IngestionRuleTests(unittest.TestCase):
    """ingestion 四规则 (a)-(d) 的负例。"""

    def test_rule_a_bad_alignment_judgment(self):
        with self.assertRaisesRegex(GoldSetValidationError, "规则 a"):
            validate_gold_set([{"tuple_kind": "alignment", "claim_text": "x",
                                "ref_text_excerpt": "y", "anchor": {"kind": "none", "value": ""},
                                "expected_judgment": "TRUE"}])

    def test_rule_b_alignment_with_constraint_fields(self):
        with self.assertRaisesRegex(GoldSetValidationError, "规则 b"):
            validate_gold_set([{"tuple_kind": "alignment", "claim_text": "x",
                                "ref_text_excerpt": "y", "anchor": {"kind": "none", "value": ""},
                                "expected_judgment": "SUPPORTED",
                                "constraint_under_test_id": "MNC-1"}])

    def test_rule_c_constraint_without_rule_source(self):
        with self.assertRaisesRegex(GoldSetValidationError, "规则 c"):
            validate_gold_set([{"tuple_kind": "constraint", "claim_text": "x",
                                "ref_text_excerpt": None, "anchor": {"kind": "none", "value": ""},
                                "expected_judgment": "VIOLATED",
                                "constraint_under_test_id": "MNC-1"}])

    def test_rule_c_both_rule_sources_rejected(self):
        with self.assertRaisesRegex(GoldSetValidationError, "二选一"):
            validate_gold_set([{"tuple_kind": "constraint", "claim_text": "x",
                                "ref_text_excerpt": None, "anchor": {"kind": "none", "value": ""},
                                "expected_judgment": "VIOLATED",
                                "constraint_under_test_id": "MNC-1",
                                "constraint_under_test_rule_text": "r",
                                "manifest_fixture_path": "p.json"}])

    def test_rule_d_bad_tuple_kind(self):
        with self.assertRaisesRegex(GoldSetValidationError, "规则 d"):
            validate_gold_set([{"tuple_kind": "mixed"}])

    def test_rule_d_not_violated_floor(self):
        tuples = [{"tuple_kind": "constraint", "claim_text": f"x{i}", "ref_text_excerpt": None,
                   "anchor": {"kind": "none", "value": ""}, "expected_judgment": "VIOLATED",
                   "constraint_under_test_id": "MNC-1",
                   "constraint_under_test_rule_text": "r"} for i in range(4)]
        with self.assertRaisesRegex(GoldSetValidationError, "规则 d"):
            validate_gold_set(tuples)


if __name__ == "__main__":
    unittest.main()
