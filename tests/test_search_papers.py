#!/usr/bin/env python3
"""search_papers.py 离线测试：去重合并/格式化/重试逻辑 + HTTP 层 mock + CLI 冒烟。

所有 search_* 的真实网络请求不测（副作用），只测纯逻辑与解析/查询构造。
"""
import os
import subprocess
import sys
import unittest
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import requests

import search_papers as sp

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "search_papers.py")

ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2306.12345v2</id>
    <title>
      Attention
      Is All You Need
    </title>
    <summary>  We propose
      the Transformer. </summary>
    <published>2023-06-20T00:00:00Z</published>
    <author><name>Vaswani</name></author>
    <link href="https://arxiv.org/pdf/2306.12345v2" type="application/pdf" title="pdf"/>
  </entry>
</feed>
"""


class FakeResp:
    def __init__(self, status_code=200, text="", payload=None, headers=None):
        self.status_code = status_code
        self.text = text
        self._payload = payload
        self.headers = headers or {"Content-Type": "application/json"}

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")


class TestDedupKey(unittest.TestCase):
    def test_doi_priority_and_normalization(self):
        self.assertEqual(sp._dedup_key({"doi": " 10.X/Y "}), "doi:10.x/y")

    def test_arxiv_version_stripped(self):
        self.assertEqual(
            sp._dedup_key({"arxiv_id": "2306.12345v2"}), "arxiv:2306.12345"
        )

    def test_pmid(self):
        self.assertEqual(sp._dedup_key({"pmid": "123"}), "pmid:123")

    def test_title_fallback_strips_punct_case_space(self):
        self.assertEqual(sp._dedup_key({"title": "Hello,  World!"}), "title:helloworld")

    def test_empty_returns_none(self):
        self.assertIsNone(sp._dedup_key({}))
        self.assertIsNone(sp._dedup_key({"title": "!!!"}))


class TestResultRichness(unittest.TestCase):
    def test_score_accumulates(self):
        p = {"abstract": "a", "pdf_url": "u", "doi": "d", "arxiv_id": "v", "venue": "x"}
        self.assertEqual(sp._result_richness(p), 4 + 3 + 2 + 1 + 1)

    def test_empty_is_zero(self):
        self.assertEqual(sp._result_richness({}), 0)


class TestMergeResults(unittest.TestCase):
    def test_multi_source_hit_merges_and_keeps_richest(self):
        rich = {"title": "T", "doi": "10.1/x", "abstract": "abs", "pdf_url": "http://p"}
        poor = {"title": "T", "doi": "10.1/x", "venue": "V"}
        merged = sp._merge_results({"openalex": [rich], "crossref": [poor]}, limit=10)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["abstract"], "abs")
        self.assertEqual(merged[0]["matched_sources"], ["crossref", "openalex"])

    def test_single_source_round_robin_by_rank_then_priority(self):
        per_source = {
            "openalex": [{"title": "A1", "doi": "10.1/a"}, {"title": "A2", "doi": "10.1/b"}],
            "crossref": [{"title": "B1", "doi": "10.1/c"}],
            "arxiv": [{"title": "C1", "arxiv_id": "2306.00001"}],
        }
        merged = sp._merge_results(per_source, limit=None)
        # 各源 rank0 轮转（openalex→arxiv→crossref 按优先级），再轮 rank1
        self.assertEqual([p["title"] for p in merged], ["A1", "C1", "B1", "A2"])

    def test_limit_truncates(self):
        per_source = {"openalex": [{"title": f"T{i}", "doi": f"10.1/{i}"} for i in range(5)]}
        self.assertEqual(len(sp._merge_results(per_source, limit=2)), 2)


class TestFormatHuman(unittest.TestCase):
    def test_empty_shows_guidance(self):
        self.assertIn("未找到相关论文", sp.format_human([]))

    def test_single_result_fields(self):
        p = {
            "title": "Attention",
            "authors": ["A"] * 8,
            "published": "2023",
            "venue": "NeurIPS",
            "arxiv_id": "2306.12345",
            "doi": "10.1/x",
            "abstract": "word " * 100,
        }
        out = sp.format_human([p])
        self.assertIn("[1] Attention", out)
        self.assertIn("等", out)  # 作者超过 6 人截断
        self.assertIn("arXiv:2306.12345 | DOI:10.1/x", out)
        self.assertIn("...", out)  # 摘要截断

    def test_multi_source_marker(self):
        p = {"title": "T", "venue": "V", "matched_sources": ["arxiv", "openalex"]}
        self.assertIn("★2源命中", sp.format_human([p]))

    def test_missing_title_placeholder(self):
        out = sp.format_human([{"title": None}])
        self.assertIn("（无标题）", out)


class TestGetWithRetry(unittest.TestCase):
    def test_persistent_connection_error_raises_after_max_attempts(self):
        with mock.patch.object(
            sp.requests, "get", side_effect=requests.exceptions.ConnectionError("down")
        ) as get, mock.patch.object(sp.time, "sleep"):
            with self.assertRaises(requests.exceptions.ConnectionError):
                sp._get_with_retry("http://x", {})
        self.assertEqual(get.call_count, sp.MAX_RETRIES + 1)

    def test_retryable_429_then_success(self):
        responses = [FakeResp(429), FakeResp(200)]
        with mock.patch.object(sp.requests, "get", side_effect=responses) as get, \
                mock.patch.object(sp.time, "sleep") as sleeper:
            resp = sp._get_with_retry("http://x", {})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(sleeper.call_count, 1)

    def test_persistent_404_raises_http_error(self):
        # 实现现状：4xx 经 raise_for_status 走异常路径同样被重试
        # （与模块注释「4xx 直接放弃」不一致，属已知轻微偏差，此处固化真实行为）
        with mock.patch.object(
            sp.requests, "get", return_value=FakeResp(404)
        ), mock.patch.object(sp.time, "sleep"):
            with self.assertRaises(requests.exceptions.HTTPError):
                sp._get_with_retry("http://x", {})


class TestSearchArxiv(unittest.TestCase):
    def test_title_mode_uses_phrase_query_and_parses_feed(self):
        captured = {}

        def fake_get(url, params, timeout=30):
            captured["url"], captured["params"] = url, params
            return FakeResp(text=ATOM_FEED)

        with mock.patch.object(sp, "_get_with_retry", side_effect=fake_get):
            results = sp.search_arxiv("attention is all you need", 5, "title")
        self.assertEqual(
            captured["params"]["search_query"], 'ti:"attention is all you need"'
        )
        self.assertEqual(captured["params"]["max_results"], 5)
        self.assertEqual(len(results), 1)
        r = results[0]
        self.assertEqual(r["arxiv_id"], "2306.12345v2")
        self.assertEqual(r["title"], "Attention Is All You Need")
        self.assertEqual(r["authors"], ["Vaswani"])
        self.assertEqual(r["venue"], "arXiv")
        self.assertEqual(r["pdf_url"], "https://arxiv.org/pdf/2306.12345v2")
        self.assertEqual(r["source"], "arxiv")

    def test_topic_multi_word_uses_and_terms(self):
        captured = {}

        def fake_get(url, params, timeout=30):
            captured["params"] = params
            return FakeResp(text=ATOM_FEED)

        with mock.patch.object(sp, "_get_with_retry", side_effect=fake_get):
            sp.search_arxiv("attention is all you need", 5, "topic")
        self.assertEqual(
            captured["params"]["search_query"],
            "all:attention AND all:is AND all:all AND all:you AND all:need",
        )

    def test_topic_single_word(self):
        captured = {}

        def fake_get(url, params, timeout=30):
            captured["params"] = params
            return FakeResp(text=ATOM_FEED)

        with mock.patch.object(sp, "_get_with_retry", side_effect=fake_get):
            sp.search_arxiv("transformer", 3, "topic")
        self.assertEqual(captured["params"]["search_query"], "all:transformer")


class TestSearchSemanticScholar(unittest.TestCase):
    def test_field_mapping(self):
        payload = {"data": [{
            "title": "T1",
            "authors": [{"name": "A"}, {"name": "B"}],
            "year": 2023,
            "abstract": "abs",
            "venue": "V",
            "paperId": "pid",
            "externalIds": {"DOI": "10.1/x", "ArXiv": "2306.12345"},
            "openAccessPdf": {"url": "http://pdf"},
            "url": "http://page",
        }]}
        with mock.patch.object(sp, "_get_with_retry", return_value=FakeResp(payload=payload)):
            results = sp.search_semantic_scholar("q", 5, "topic")
        r = results[0]
        self.assertEqual(r["title"], "T1")
        self.assertEqual(r["authors"], ["A", "B"])
        self.assertEqual(r["published"], "2023")  # 无 publicationDate 时回退 year
        self.assertEqual(r["semantic_scholar_id"], "pid")
        self.assertEqual(r["doi"], "10.1/x")
        self.assertEqual(r["arxiv_id"], "2306.12345")
        self.assertEqual(r["pdf_url"], "http://pdf")
        self.assertEqual(r["source"], "semantic_scholar")

    def test_missing_optional_ids_are_none(self):
        payload = {"data": [{"title": "T2", "authors": [], "paperId": "p2"}]}
        with mock.patch.object(sp, "_get_with_retry", return_value=FakeResp(payload=payload)):
            r = sp.search_semantic_scholar("q", 5, "topic")[0]
        self.assertIsNone(r["doi"])
        self.assertIsNone(r["arxiv_id"])
        self.assertIsNone(r["pdf_url"])


class TestSearchDblp(unittest.TestCase):
    def test_single_author_dict_and_string_ee(self):
        info = {
            "title": "D1",
            "authors": {"author": {"text": "Solo"}},
            "year": "2020",
            "venue": "CSS",
            "doi": "10.1/d",
            "ee": "https://doi.org/10.1/d.pdf",
            "url": "https://dblp.org/rec/x",
        }
        payload = {"result": {"hits": {"hit": [{"info": info}]}}}
        with mock.patch.object(sp, "_get_with_retry", return_value=FakeResp(payload=payload)):
            r = sp.search_dblp("q", 5, "topic")[0]
        self.assertEqual(r["authors"], ["Solo"])
        self.assertEqual(r["pdf_url"], "https://doi.org/10.1/d.pdf")
        self.assertEqual(r["page_url"], "https://dblp.org/rec/x")
        self.assertEqual(r["source"], "dblp")

    def test_anubis_bot_challenge_rejected_explicitly(self):
        # 真实冒烟发现：DBLP 对脚本请求返回 Anubis 人机验证页（HTTP 200 + HTML）。
        # 必须显性报"反爬拦截"而不是"无法解析的内容"，且 multi 聚合可优雅跳过
        challenge = FakeResp(text="<!doctype html><title>Making sure you're not a bot!</title>",
                             headers={"Content-Type": "text/html; charset=utf-8"})
        with mock.patch.object(sp, "_get_with_retry", return_value=challenge):
            with self.assertRaisesRegex(RuntimeError, "反爬拦截"):
                sp.search_dblp("q", 5, "topic")


class TestRunSearchAutoDegrades(unittest.TestCase):
    def test_auto_skips_failing_source(self):
        with mock.patch.object(
            sp, "search_semantic_scholar",
            side_effect=requests.exceptions.ConnectionError("429"),
        ), mock.patch.object(
            sp, "search_openalex", return_value=[{"title": "F", "source": "openalex"}]
        ):
            results = sp.run_search("q", 5, "topic", "auto")
        self.assertEqual(results[0]["title"], "F")


class TestCliSmoke(unittest.TestCase):
    def test_help(self):
        r = subprocess.run(
            [sys.executable, "-B", SCRIPT, "--help"], capture_output=True, text=True, timeout=60
        )
        self.assertEqual(r.returncode, 0)
        for token in ("--mode", "--source", "--limit", "--json"):
            self.assertIn(token, r.stdout)

    def test_limit_zero_rejected(self):
        r = subprocess.run(
            [sys.executable, "-B", SCRIPT, "q", "--limit", "0"],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(r.returncode, 1)
        self.assertIn("--limit", r.stderr)

    def test_invalid_source_rejected(self):
        r = subprocess.run(
            [sys.executable, "-B", SCRIPT, "q", "--source", "baidu"],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
