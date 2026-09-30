#!/usr/bin/env python3
"""html2md.py 离线测试：用构造的 LaTeXML 风格 HTML 验证真实 HTML→Markdown 转换。

依赖 bs4+lxml（本环境可用），无任何网络请求。
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from bs4 import BeautifulSoup

import html2md as h2m

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "html2md.py")

PAPER_HTML = """<html><head><title>Old Title</title>
<meta name="citation_title" content="Test Paper">
<meta name="citation_author" content="Alice">
<meta name="citation_author" content="Bob">
<meta name="citation_date" content="2026-01-01">
<meta name="citation_abstract" content="Short abstract.">
</head><body>
<div class="ltx_page_main"><div class="ltx_page_content"><article>
<section class="ltx_abstract" id="abstract">
<p class="ltx_p">We study things.</p>
</section>
<section class="ltx_section" id="s1">
<h2 class="ltx_title ltx_title_section"><span class="ltx_tag ltx_tag_section">1</span>Introduction</h2>
<p class="ltx_p">We show <span class="ltx_font_bold">bold claim</span> and
<math class="ltx_Math" alttext="x^2" display="inline"><mi>x</mi></math> works
<a href="#bib.bib1">[1]</a>.</p>
<figure class="ltx_equation ltx_align_center" id="eq1">
<math alttext="E=mc^2" display="block"><annotation encoding="application/x-tex">E=mc^2</annotation></math>
</figure>
<figure class="ltx_figure" id="fig1">
<img class="ltx_graphics" src="x1.png"/>
<figcaption class="ltx_caption">Figure 1: A figure of cats</figcaption>
</figure>
<figure class="ltx_table" id="t1">
<table class="ltx_tabular"><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>
</figure>
<ul class="ltx_itemize" id="lis">
<li class="ltx_item" id="li1"><span class="ltx_tag ltx_tag_item">• </span><span class="ltx_p">item one</span></li>
</ul>
</section>
<section class="ltx_bibliography" id="bib">
<ul class="ltx_biblist">
<li class="ltx_bibitem" id="bib.bib1"><span class="ltx_tag ltx_tag_bibitem">[1]</span>Some reference about things.</li>
</ul>
</section>
</article></div></div></body></html>"""

ABS_HTML = """<html><head>
<meta name="citation_title" content="ABS Title Override">
<meta name="citation_author" content="Carol">
</head><body></body></html>"""


class TestGetLatex(unittest.TestCase):
    def _math(self, html):
        return BeautifulSoup(html, "lxml").find("math")

    def test_alttext_priority(self):
        el = self._math(
            '<math alttext="x^2"><annotation encoding="application/x-tex">y</annotation></math>'
        )
        self.assertEqual(h2m._get_latex(el), "x^2")

    def test_annotation_fallback(self):
        el = self._math(
            '<math><annotation encoding="application/x-tex">E=mc^2</annotation></math>'
        )
        self.assertEqual(h2m._get_latex(el), "E=mc^2")

    def test_missing_returns_empty(self):
        self.assertEqual(h2m._get_latex(self._math("<math></math>")), "")


class TestStripHttpHeaders(unittest.TestCase):
    def test_http_11_headers_stripped(self):
        self.assertEqual(h2m._strip_http_headers("HTTP/1.1 200 OK\n\n<html></html>"),
                         "<html></html>")

    def test_h2_headers_stripped(self):
        self.assertEqual(h2m._strip_http_headers("h2 200\n\nbody"), "body")

    def test_plain_html_unchanged(self):
        self.assertEqual(h2m._strip_http_headers("<html></html>"), "<html></html>")


class TestConvertEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.md = h2m.ArxivHTML2Markdown("2606.00001").convert(PAPER_HTML)

    def test_frontmatter_from_citation_meta(self):
        self.assertIn('arxiv_id: "2606.00001"', self.md)
        self.assertIn("# Test Paper", self.md)
        self.assertIn("**Authors**: Alice, Bob", self.md)
        self.assertIn("**Date**: 2026-01-01", self.md)
        self.assertIn("https://arxiv.org/abs/2606.00001", self.md)

    def test_abstract_section(self):
        self.assertIn("## Abstract", self.md)
        self.assertIn("We study things.", self.md)

    def test_section_heading_with_tag_span_stripped(self):
        self.assertIn("## Introduction", self.md)

    def test_inline_conversion(self):
        self.assertIn("**bold claim**", self.md)
        self.assertIn("$x^2$", self.md)
        self.assertIn("[1]", self.md)  # 引文链接转编号

    def test_block_equation(self):
        self.assertIn("$$\nE=mc^2\n$$", self.md)

    def test_figure_with_arxiv_url(self):
        self.assertIn("![Figure 1: A figure of cats](https://arxiv.org/html/x1.png)", self.md)

    def test_table_with_header_separator(self):
        self.assertIn("| A | B |", self.md)
        self.assertIn("| --- | --- |", self.md)
        self.assertIn("| 1 | 2 |", self.md)

    def test_list(self):
        self.assertIn("- item one", self.md)

    def test_bibliography(self):
        self.assertIn("## References", self.md)
        self.assertIn("1. Some reference about things.", self.md)

    def test_nav_and_toc_skipped(self):
        self.assertNotIn("ltx_TOC", self.md)


class TestTableEdgeCases(unittest.TestCase):
    def _convert(self, table_html):
        # 直接对 <table> 元素测 _convert_table（顶层裸 table 在源码中会被跳过，
        # 实际文档中表格总是包在 <figure class="ltx_table"> 里）
        soup = BeautifulSoup(f"<div>{table_html}</div>", "lxml")
        el = soup.find("table")
        return h2m.ArxivHTML2Markdown("1")._convert_table(el)

    def test_rowspan_pads_following_rows(self):
        md = self._convert(
            "<table><tr><td rowspan='2'>R</td><td>A</td></tr>"
            "<tr><td>B</td></tr></table>"
        )
        self.assertIn("| R | A |", md)
        self.assertIn("|  | B |", md)

    def test_colspan_expands_cells(self):
        md = self._convert("<table><tr><td colspan='2'>W</td><td>Z</td></tr></table>")
        self.assertIn("| W | W | Z |", md)


class TestMetaHelpers(unittest.TestCase):
    def test_load_meta_from_abs(self):
        meta = h2m.load_meta_from_abs(ABS_HTML)
        self.assertEqual(meta["title"], "ABS Title Override")
        self.assertEqual(meta["authors"], ["Carol"])

    def test_convert_file_writes_output(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "paper.html")
            src.write_text(PAPER_HTML, encoding="utf-8")
            out = Path(d, "paper.md")
            md = h2m.convert_file(str(src), "2606.00001", str(out))
            self.assertTrue(out.is_file())
            self.assertEqual(out.read_text(encoding="utf-8"), md)
            self.assertTrue(md.startswith("---\n"))

    def test_meta_source_overrides_title(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "paper.html")
            src.write_text(PAPER_HTML, encoding="utf-8")
            abs_src = Path(d, "abs.html")
            abs_src.write_text(ABS_HTML, encoding="utf-8")
            md = h2m.convert_file(str(src), "2606.00001", meta_source=str(abs_src))
        self.assertIn("# ABS Title Override", md)
        self.assertIn("**Authors**: Carol", md)


class TestCliSmoke(unittest.TestCase):
    def test_help(self):
        r = subprocess.run(
            [sys.executable, "-B", SCRIPT, "--help"], capture_output=True, text=True, timeout=60
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("--meta", r.stdout)


if __name__ == "__main__":
    unittest.main()
