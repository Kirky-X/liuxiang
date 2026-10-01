#!/usr/bin/env python3
"""citation_graph.py 离线测试：DOI 归一化、边解析、人类可读输出 + HTTP mock + CLI 冒烟。

OpenCitations 真实网络请求不测（副作用），只测纯逻辑。
"""
import os
import subprocess
import sys
import unittest
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import requests

import citation_graph as cg

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "citation_graph.py")

EDGES = [
    {
        "oci": "06023129539-06202880635",
        "citing": "omid:br/06023129539 arxiv:2601.17238",
        "cited": "omid:br/06202880635 doi:10.1145/3025453.3025717 openalex:W2611339666",
        "creation": "2026",
        "timespan": "P8Y",
        "journal_sc": "no",
        "author_sc": "no",
    },
    {
        "oci": "0605288213-06202880635",
        "citing": "omid:br/0605288213 doi:10.1109/vr59515.2025.00081",
        "cited": "omid:br/06202880635 doi:10.1145/3025453.3025717",
        "creation": "2025",
        "timespan": "P7Y",
        "journal_sc": "no",
        "author_sc": "no",
    },
]


class FakeResp:
    def __init__(self, status_code=200, text="[]", payload=None):
        self.status_code = status_code
        self.text = text
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")


class TestNormalizeDoi(unittest.TestCase):
    def test_bare_doi(self):
        self.assertEqual(cg.normalize_doi("10.1145/3025453.3025717"), "10.1145/3025453.3025717")

    def test_doi_prefix(self):
        self.assertEqual(cg.normalize_doi("doi:10.1234/x"), "10.1234/x")

    def test_doi_org_url(self):
        self.assertEqual(cg.normalize_doi("https://doi.org/10.1145/x"), "10.1145/x")
        self.assertEqual(cg.normalize_doi("http://dx.doi.org/10.1145/x"), "10.1145/x")

    def test_garbage_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "无法识别的 DOI"):
            cg.normalize_doi("2306.12345")
        with self.assertRaisesRegex(RuntimeError, "无法识别的 DOI"):
            cg.normalize_doi("https://chinaxiv.org/abs/202410.00098")


class TestFetchEdges(unittest.TestCase):
    def test_citations_endpoint_url(self):
        with mock.patch.object(cg, "_get_with_retry", return_value=FakeResp(payload=EDGES)) as g:
            edges = cg.fetch_edges("10.1145/x", "citations")
        self.assertEqual(len(edges), 2)
        self.assertIn("/citations/doi:10.1145/x", g.call_args[0][0])

    def test_references_endpoint_url(self):
        with mock.patch.object(cg, "_get_with_retry", return_value=FakeResp(payload=EDGES)) as g:
            cg.fetch_edges("10.1145/x", "references")
        self.assertIn("/references/doi:10.1145/x", g.call_args[0][0])

    def test_empty_body_returns_empty_list(self):
        with mock.patch.object(cg, "_get_with_retry", return_value=FakeResp(text="")):
            self.assertEqual(cg.fetch_edges("10.1/none", "citations"), [])

    def test_404_response_returns_empty_not_error(self):
        # 架构审查 H1 回归：404 必须在 _get_with_retry 层原样返回（不 raise），
        # fetch_edges 转空列表——文档承诺「未收录 DOI 返回空，不是错误」
        with mock.patch.object(cg, "_get_with_retry", return_value=FakeResp(status_code=404, text="")):
            self.assertEqual(cg.fetch_edges("10.12074/202410.00098", "citations"), [])

    def test_other_4xx_still_raises(self):
        # 403 等其他 4xx 由 _get_with_retry 的 raise_for_status 抛出（不误当空结果）
        with mock.patch.object(cg.requests, "get", return_value=FakeResp(status_code=403, text="forbidden")):
            with self.assertRaises(requests.exceptions.HTTPError):
                cg.fetch_edges("10.1/none", "references")

    def test_dict_payload_treated_as_empty(self):
        with mock.patch.object(cg, "_get_with_retry", return_value=FakeResp(text="{}", payload={})):
            self.assertEqual(cg.fetch_edges("10.1/none", "references"), [])


class TestSummarizeEdges(unittest.TestCase):
    def test_citations_direction_uses_citing(self):
        rows = cg.summarize_edges(EDGES, "10.1145/x", "citations")
        # citing 侧无 DOI 的边保留原始标识符
        self.assertEqual(rows[0]["identifier"], "omid:br/06023129539 arxiv:2601.17238")
        self.assertEqual(rows[1]["identifier"], "10.1109/vr59515.2025.00081")
        self.assertEqual(rows[1]["year"], "2025")

    def test_references_direction_uses_cited(self):
        rows = cg.summarize_edges(EDGES, "10.1145/x", "references")
        self.assertEqual(rows[0]["identifier"], "10.1145/3025453.3025717")
        self.assertEqual(rows[1]["identifier"], "10.1145/3025453.3025717")

    def test_top_cap(self):
        many = [dict(EDGES[0]) for _ in range(30)]
        rows = cg.summarize_edges(many, "10.1145/x", "citations", top=5)
        self.assertEqual(len(rows), 5)


class TestFormatHuman(unittest.TestCase):
    def test_empty_shows_explicit_not_an_error_note(self):
        out = cg.format_human("10.1/none", [], [])
        self.assertIn("未收录", out)
        self.assertIn("不是错误", out)

    def test_nonempty_lists_edges(self):
        cit = cg.summarize_edges(EDGES, "10.1145/x", "citations")
        out = cg.format_human("10.1145/x", cit, [])
        self.assertIn("10.1109/vr59515.2025.00081", out)
        self.assertIn("P7Y", out)


class TestCliSmoke(unittest.TestCase):
    def test_help(self):
        r = subprocess.run(
            [sys.executable, "-B", SCRIPT, "--help"], capture_output=True, text=True, timeout=60
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("direction", r.stdout)

    def test_bad_doi_exits_1(self):
        r = subprocess.run(
            [sys.executable, "-B", SCRIPT, "not-a-doi"],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(r.returncode, 1)
        self.assertIn("无法识别的 DOI", r.stderr)


if __name__ == "__main__":
    unittest.main()
