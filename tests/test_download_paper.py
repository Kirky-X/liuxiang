#!/usr/bin/env python3
"""download_paper.py 离线测试：标识符识别、SSRF 防护、tar 安全解压、LaTeX 处理、Markdown 组装。

真实网络下载与 pandoc 转换不测（副作用），见 SKIPPED.md。
"""
import io
import os
import socket
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import ipaddress

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import download_paper as dp

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "download_paper.py")


class TestSlugify(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(dp.slugify("Hello World"), "hello-world")

    def test_punct_and_whitespace_collapsed(self):
        self.assertEqual(dp.slugify("A  B_c-d!"), "a-b-c-d")

    def test_empty_falls_back(self):
        self.assertEqual(dp.slugify(""), "paper")
        self.assertEqual(dp.slugify("!!!"), "paper")

    def test_truncated_to_80(self):
        self.assertEqual(dp.slugify("x" * 100), "x" * 80)


class TestIdentifierRegexes(unittest.TestCase):
    def test_arxiv_new_format(self):
        for ident, gid in (("2306.12345", "2306.12345"), ("2306.12345v2", "2306.12345v2")):
            m = dp.ARXIV_ID_RE.match(ident)
            self.assertIsNotNone(m, ident)
            self.assertEqual(m.group(2), gid)

    def test_arxiv_prefix_case_insensitive(self):
        self.assertEqual(dp.ARXIV_ID_RE.match("arXiv:2306.12345").group(2), "2306.12345")

    def test_arxiv_old_format(self):
        self.assertIsNotNone(dp.ARXIV_ID_RE.match("hep-th/9901001"))
        self.assertIsNotNone(dp.ARXIV_ID_RE.match("math.GT/0309136"))

    def test_arxiv_rejects_doi_and_garbage(self):
        for ident in ("10.1145/3025453.3025717", "hello", "2306.12", "2306.12345v"):
            self.assertIsNone(dp.ARXIV_ID_RE.match(ident), ident)

    def test_doi_format(self):
        self.assertIsNotNone(dp.DOI_RE.match("10.1145/3025453.3025717"))
        self.assertIsNone(dp.DOI_RE.match("9.1234/x"))
        self.assertIsNone(dp.DOI_RE.match("10.1234"))


class TestIpRejectReason(unittest.TestCase):
    def test_rejected_addresses(self):
        for ip in ("127.0.0.1", "10.0.0.5", "192.168.1.1", "172.16.0.9",
                   "169.254.3.3", "224.0.0.5", "0.0.0.0", "::1", "fd00::1"):
            self.assertIsNotNone(
                dp._ip_reject_reason(ipaddress.ip_address(ip)), ip
            )

    def test_public_allowed(self):
        for ip in ("8.8.8.8", "1.1.1.1", "2606:4700::1111"):
            self.assertIsNone(dp._ip_reject_reason(ipaddress.ip_address(ip)), ip)


class TestValidatePublicHttpUrl(unittest.TestCase):
    def test_non_http_scheme_rejected(self):
        with self.assertRaises(RuntimeError):
            dp.validate_public_http_url("ftp://example.com/a.pdf")

    def test_missing_host_rejected(self):
        with self.assertRaises(RuntimeError):
            dp.validate_public_http_url("http:///no-host")

    def test_local_and_internal_hosts_rejected_before_dns(self):
        for host in ("localhost", "sub.localhost", "box.local", "box.internal"):
            with self.assertRaises(RuntimeError, msg=host):
                dp.validate_public_http_url(f"http://{host}/a")

    def test_private_resolved_ip_rejected(self):
        infos = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.1", 80))]
        with mock.patch.object(dp.socket, "getaddrinfo", return_value=infos):
            with self.assertRaises(RuntimeError):
                dp.validate_public_http_url("http://attacker.example/a.pdf")

    def test_public_resolved_ip_passes(self):
        infos = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 80))]
        with mock.patch.object(dp.socket, "getaddrinfo", return_value=infos):
            dp.validate_public_http_url("https://arxiv.org/pdf/2306.12345")


def _build_tar(members):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, data, kind in members:
            info = tarfile.TarInfo(name)
            if kind == "file":
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            elif kind == "dir":
                info.type = tarfile.DIRTYPE
                tar.addfile(info)
            elif kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = "/etc/passwd"
                tar.addfile(info)
    buf.seek(0)
    return buf


class TestExtractTarSafely(unittest.TestCase):
    MEMBERS = [
        ("good.txt", b"hello", "file"),
        ("../evil.txt", b"bad", "file"),
        ("link", b"", "symlink"),
        ("/abs.txt", b"bad", "file"),
    ]

    def test_dangerous_members_skipped_safe_extracted(self):
        with tempfile.TemporaryDirectory() as dest:
            with tarfile.open(fileobj=_build_tar(self.MEMBERS), mode="r:*") as tar:
                dp._extract_tar_safely(tar, dest)
            self.assertEqual(Path(dest, "good.txt").read_bytes(), b"hello")
            self.assertFalse(Path(dest, "evil.txt").exists())
            self.assertFalse((Path(dest).parent / "evil.txt").exists())
            self.assertFalse(Path(dest, "abs.txt").exists())
            self.assertFalse(Path(dest, "link").exists())

    def test_nested_regular_file_extracted(self):
        with tempfile.TemporaryDirectory() as dest:
            members = [("sub/dir/a.tex", b"body", "file")]
            with tarfile.open(fileobj=_build_tar(members), mode="r:*") as tar:
                dp._extract_tar_safely(tar, dest)
            self.assertEqual(Path(dest, "sub", "dir", "a.tex").read_bytes(), b"body")


class TestFindMainTex(unittest.TestCase):
    def test_prefers_main_tex(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "a.tex").write_text("\\documentclass{article}", encoding="utf-8")
            Path(d, "main.tex").write_text("\\documentclass{article}", encoding="utf-8")
            self.assertEqual(Path(dp._find_main_tex(d)).name, "main.tex")

    def test_falls_back_to_documentclass(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "b.tex").write_text("no class here", encoding="utf-8")
            Path(d, "a.tex").write_text("\\documentclass{article}", encoding="utf-8")
            self.assertEqual(Path(dp._find_main_tex(d)).name, "a.tex")

    def test_no_tex_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(dp._find_main_tex(d))


class TestExpandInputs(unittest.TestCase):
    def test_recursive_expansion_and_ext_append(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "sections").mkdir()
            Path(d, "main.tex").write_text(
                "\\input{sections/intro}\n\\include{extra}\nEND", encoding="utf-8"
            )
            Path(d, "sections", "intro.tex").write_text(
                "INTRO \\input{more}", encoding="utf-8"
            )
            Path(d, "sections", "more.tex").write_text("MORE", encoding="utf-8")
            Path(d, "extra.tex").write_text("EXTRA", encoding="utf-8")
            out = dp._expand_inputs(d, str(Path(d, "main.tex")))
        for token in ("INTRO", "MORE", "EXTRA", "END"):
            self.assertIn(token, out)

    def test_missing_input_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "main.tex").write_text("A \\input{ghost} B", encoding="utf-8")
            out = dp._expand_inputs(d, str(Path(d, "main.tex")))
        self.assertIn("A  B", out)

    def test_cycle_terminates(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "c1.tex").write_text("C1 \\input{c2}", encoding="utf-8")
            Path(d, "c2.tex").write_text("C2 \\input{c1}", encoding="utf-8")
            out = dp._expand_inputs(d, str(Path(d, "c1.tex")))
        self.assertEqual(out.count("C1"), 1)
        self.assertEqual(out.count("C2"), 1)


class TestNormalizePandocMath(unittest.TestCase):
    def test_inline_backtick_math(self):
        self.assertEqual(dp._normalize_pandoc_math("$`x^2`$"), "$x^2$")

    def test_inline_with_backslash(self):
        self.assertEqual(
            dp._normalize_pandoc_math("$`\\alpha + \\beta`$"), "$\\alpha + \\beta$"
        )

    def test_block_equation_label_and_env_stripped(self):
        src = "```math\n\\begin{equation}\nE = mc^2 \\label{eq:1}\n\\end{equation}\n```"
        self.assertEqual(dp._normalize_pandoc_math(src), "$$\nE = mc^2\n$$")

    def test_align_star_block(self):
        src = "```math\n\\begin{align*}\na \\\\ b\n\\end{align*}\n```"
        self.assertEqual(dp._normalize_pandoc_math(src), "$$\na \\\\ b\n$$")

    def test_stray_labels_removed(self):
        out = dp._normalize_pandoc_math("x \\label{a} y")
        self.assertNotIn("\\label", out)


class TestStripLatexDivNoise(unittest.TestCase):
    def test_ccsxml_block_deleted(self):
        src = '<div class="CCSXML"><ccs2012>junk</ccs2012></div>rest'
        self.assertEqual(dp._strip_latex_div_noise(src), "rest")

    def test_div_unwrapped_keeps_content(self):
        out = dp._strip_latex_div_noise('<div class="center">\ncontent\n</div>')
        self.assertIn("content", out)
        self.assertNotIn("<div", out)

    def test_img_and_embed_to_markdown(self):
        self.assertIn(
            "![figure](fig1.png)",
            dp._strip_latex_div_noise('<img src="fig1.png" alt="x"/>'),
        )
        self.assertIn(
            "![figure](e.png)",
            dp._strip_latex_div_noise('<embed src="e.png" type="image/png"/>'),
        )

    def test_figcaption_to_italic_with_tags_stripped(self):
        out = dp._strip_latex_div_noise("<figcaption>Cap <b>text</b></figcaption>")
        self.assertIn("*Cap text*", out)

    def test_blank_lines_compressed(self):
        self.assertNotIn("\n\n\n", dp._strip_latex_div_noise("a\n\n\n\nb"))


class TestBuildMarkdown(unittest.TestCase):
    META = {
        "title": "T",
        "authors": ["A", "B"],
        "published": "2023-06-20",
        "venue": "NeurIPS",
        "abstract": "Abs text.",
    }

    def test_latex_conversion_annotated(self):
        md = dp.build_markdown(self.META, "BODY", "2306.12345", conversion="latex")
        self.assertIn("# T", md)
        self.assertIn("- **作者**: A, B", md)
        self.assertIn("- **来源/期刊**: NeurIPS", md)
        self.assertIn("LaTeX 源码", md)
        self.assertIn("## 摘要", md)
        self.assertIn("BODY", md)

    def test_pdf_conversion_annotated_and_empty_body_placeholder(self):
        md = dp.build_markdown(self.META, "", "10.1/x")
        self.assertIn("PDF 文本提取", md)
        self.assertIn("未能提取到正文文字", md)


class TestOfflineShortCircuits(unittest.TestCase):
    def test_unpaywall_skipped_without_email(self):
        with mock.patch.object(dp, "UNPAYWALL_EMAIL", ""):
            self.assertIsNone(dp.fetch_unpaywall_pdf("10.1/x"))


class TestCliSmoke(unittest.TestCase):
    def test_help(self):
        r = subprocess.run(
            [sys.executable, "-B", SCRIPT, "--help"], capture_output=True, text=True, timeout=60
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("identifier", r.stdout)

    def test_s2_fallback_identifier_error_exits_1(self):
        # 非 URL/DOI/arXiv 的标识符会兜底当 S2 paper ID 查询；
        # 用 env 把 S2 端点指到拒绝连接的本地端口，离线验证「查不到→报错退出 1」路径。
        env = dict(os.environ, S2_PAPER_URL="http://127.0.0.1:1/graph/v1/paper/{id}")
        r = subprocess.run(
            [sys.executable, "-B", SCRIPT, "not-a-real-s2-id"],
            capture_output=True, text=True, timeout=120, env=env,
        )
        self.assertEqual(r.returncode, 1)
        self.assertIn("错误", r.stderr)


if __name__ == "__main__":
    unittest.main()
