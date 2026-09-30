#!/usr/bin/env python3
"""pdf2md.py 离线测试：文本清理纯函数 + pymupdf 生成 PDF 的图片提取 + CLI 冒烟。

真实 pandoc/pdftotext/pdfminer 转换后端与 URL 下载不测（副作用），见 SKIPPED.md。
"""
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import pdf2md

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "pdf2md.py")


def _make_png(width, height):
    """纯 stdlib 生成 RGB 噪声 PNG（随机噪声保证压缩后仍超过 5KB 图标阈值）。"""
    def chunk(typ, data):
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + os.urandom(width * 3) for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


class TestCleanupText(unittest.TestCase):
    def test_removes_artifacts_keeps_prose(self):
        text = "Hello \fWorld\n42\n. . . .\nx\n\nReal line\n"
        self.assertEqual(pdf2md.cleanup_text(text), "Hello World\nReal line")

    def test_page_number_threshold(self):
        # 5 位数数字行不是页码，保留
        self.assertIn("12345", pdf2md.cleanup_text("12345\nkeep"))

    def test_short_dot_leader_kept(self):
        # 仅点号且长度 ≤2 不满足删除条件（len > 2），且保留原始行内容
        self.assertEqual(pdf2md.cleanup_text(".. \nkeep\n"), ".. \nkeep")


class TestRemoveTocBlock(unittest.TestCase):
    def _toc_lines(self, n):
        return [f"{i} Chapter {i} overview of things" for i in range(1, n + 1)]

    def test_removes_toc_block_with_heading(self):
        text = ("Intro paragraph\n\nContents\n\n"
                + "\n".join(self._toc_lines(12))
                + "\n\nBody text after toc\n")
        out = pdf2md.remove_toc_block(text)
        self.assertNotIn("Contents", out)
        self.assertNotIn("Chapter 1 overview", out)
        self.assertIn("Intro paragraph", out)
        self.assertIn("Body text after toc", out)

    def test_few_toc_like_lines_kept(self):
        text = ("Title line\n\n"
                + "\n".join(self._toc_lines(3))
                + "\n\nBody A\nBody B\n")
        self.assertEqual(pdf2md.remove_toc_block(text), text)


class TestAddStructureHeuristics(unittest.TestCase):
    def test_references_heading(self):
        self.assertIn("## References", pdf2md.add_structure_heuristics("References\n"))

    def test_abstract_heading(self):
        self.assertIn("## Abstract", pdf2md.add_structure_heuristics("Abstract\n"))

    def test_numbered_section_depth2(self):
        self.assertIn("## 1 Introduction", pdf2md.add_structure_heuristics("1 Introduction\n"))

    def test_dotted_section_depth3(self):
        # 结构前缀白名单只含 1/1./1.1 开头，1.1 触发点分深度
        self.assertIn("### 1.1 Methods", pdf2md.add_structure_heuristics("1.1 Methods\n"))

    def test_deep_numbering_not_in_whitelist_untouched(self):
        # 前缀白名单只有 1/1./1.1，"1.1.2" 不命中（第 4 字符是 '.' 非空格），保持原样
        self.assertEqual(
            pdf2md.add_structure_heuristics("1.1.2 Details\n"), "1.1.2 Details\n"
        )

    def test_long_lines_and_prose_untouched(self):
        long_line = "1 " + "x" * 90
        text = long_line + "\nplain sentence without markers\n"
        self.assertEqual(pdf2md.add_structure_heuristics(text), text)


class TestBuildMarkdown(unittest.TestCase):
    def test_frontmatter_fields(self):
        md = pdf2md.build_markdown("2605.28042", "BODY")
        self.assertTrue(md.startswith("---\n"))
        self.assertIn('arxiv_id: "2605.28042"', md)
        self.assertIn('source_url: "https://arxiv.org/abs/2605.28042"', md)
        self.assertIn('conversion: "pdf"', md)
        self.assertTrue(md.endswith("BODY"))


class TestDownloadPdfSchemeGuard(unittest.TestCase):
    def test_file_scheme_rejected(self):
        with self.assertRaises(ValueError):
            pdf2md.download_pdf("file:///etc/passwd", Path("/tmp/x.pdf"))

    def test_ftp_scheme_rejected(self):
        with self.assertRaises(ValueError):
            pdf2md.download_pdf("ftp://host/x.pdf", Path("/tmp/x.pdf"))


class TestConvertRawTextFallback(unittest.TestCase):
    def test_printable_bytes_extracted(self):
        # pdftotext 缺失或对垃圾字节失败时，走原始字节提取兜底
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"Hello\x00\x01World\x7f!")
            path = f.name
        try:
            self.assertEqual(pdf2md.convert_raw_text(Path(path)), "Hello World !")
        finally:
            os.unlink(path)


class TestExtractPdfImages(unittest.TestCase):
    def setUp(self):
        try:
            import pymupdf  # noqa: F401
        except ImportError:
            self.skipTest("pymupdf 未安装")

    def test_extract_dedup_and_small_icon_skip(self):
        import pymupdf

        big = _make_png(200, 200)   # 噪声 PNG，>5KB
        tiny = _make_png(8, 8)      # 装饰性小图标，<5KB
        self.assertGreater(len(big), 5000)
        self.assertLess(len(tiny), 5000)

        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_image(pymupdf.Rect(50, 50, 250, 250), stream=big)
        page.insert_image(pymupdf.Rect(300, 50, 500, 250), stream=big)
        page.insert_image(pymupdf.Rect(50, 300, 110, 360), stream=tiny)
        with tempfile.TemporaryDirectory() as d:
            pdf_path = Path(d, "sample.pdf")
            doc.save(str(pdf_path))
            doc.close()

            images_dir = Path(d, "images")
            result = pdf2md.extract_pdf_images(pdf_path, images_dir)
            self.assertEqual(list(result.keys()), [1])
            self.assertEqual(len(result[1]), 1)
            saved = images_dir / result[1][0]
            self.assertTrue(saved.is_file())
            self.assertGreater(saved.stat().st_size, 5000)


class TestCliSmoke(unittest.TestCase):
    def test_help(self):
        r = subprocess.run(
            [sys.executable, "-B", SCRIPT, "--help"], capture_output=True, text=True, timeout=60
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("pdf_source", r.stdout)


if __name__ == "__main__":
    unittest.main()
