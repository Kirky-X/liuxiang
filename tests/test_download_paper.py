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


CHINAXIV_PAGE = """
<html><head><title>ChinaXiv.org 中国科学院科技论文预发布平台</title></head><body>
<a style="color:blue;margin-left:45px;" href="http://dx.doi.org/10.12074/202410.00098">
<font color="blue">DOI:10.12074/202410.00098</font></a>
<span> 葛枭语.所谓影响关系有待商榷：对温忠麟等人（2024）的评论.中国科学院科技论文预发布平台.[DOI:10.12074/202410.00098]</span>
<div><b>摘要: </b>温忠麟等人（2024）在《心理学报》发文聚焦长期以来用法模糊的“影响”一词。
</div>
<a href="/user/download.htm?uuid=74c68db5-af96-4d4e-8c41-45b94159cfbe">附件</a>
<a href="/user/download.htm?uuid=daf9c3c1-e67a-45aa-b5a7-20c953d98670&filetype=bib">BibTeX</a>
<a href="/user/download.htm?uuid=daf9c3c1-e67a-45aa-b5a7-20c953d98670&filetype=pdf">PDF</a>
<a href="/user/download.htm?uuid=daf9c3c1-e67a-45aa-b5a7-20c953d98670&filetype=zip">源码</a>
</body></html>
"""


class FakeChinaXivResp:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text
        self.content = text.encode("utf-8")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")


class TestChinaXiv(unittest.TestCase):
    def test_id_regex(self):
        self.assertTrue(dp.CHINAXIV_ID_RE.match("202410.00098"))
        self.assertTrue(dp.CHINAXIV_ID_RE.match("chinaxiv:202410.00098v2"))
        self.assertTrue(dp.CHINAXIV_ID_RE.match("202010.0001V3"))
        # arXiv 是 4 位月前缀，不得与 ChinaXiv 的 6 位年月前缀混淆
        self.assertFalse(dp.CHINAXIV_ID_RE.match("2306.12345"))
        self.assertFalse(dp.CHINAXIV_ID_RE.match("not-an-id"))

    def test_url_regex(self):
        m = dp.CHINAXIV_URL_RE.match("https://chinaxiv.org/abs/202410.00098v2")
        self.assertEqual(m.group(1), "202410.00098v2")
        m = dp.CHINAXIV_URL_RE.match("http://www.chinaxiv.org/abs/202010.0001")
        self.assertEqual(m.group(1), "202010.0001")
        self.assertFalse(dp.CHINAXIV_URL_RE.match("https://arxiv.org/abs/2306.12345"))

    def test_page_parses_metadata_and_pdf_uuid(self):
        with mock.patch.object(dp, "_get_with_retry", return_value=FakeChinaXivResp(text=CHINAXIV_PAGE)):
            meta, pdf_url = dp.resolve_chinaxiv("202410.00098")
        self.assertEqual(meta["title"], "所谓影响关系有待商榷：对温忠麟等人（2024）的评论")
        self.assertEqual(meta["authors"], ["葛枭语"])
        self.assertEqual(meta["doi"], "10.12074/202410.00098")
        self.assertIn("温忠麟等人（2024）", meta["abstract"])
        self.assertEqual(meta["venue"], "ChinaXiv（中科院预印本）")
        self.assertEqual(
            pdf_url,
            f"{dp.CHINAXIV_BASE_URL}/user/download.htm"
            "?uuid=daf9c3c1-e67a-45aa-b5a7-20c953d98670&filetype=pdf",
        )

    def test_page_without_pdf_link_raises(self):
        page = CHINAXIV_PAGE.replace("&filetype=pdf", "")
        with mock.patch.object(dp, "_get_with_retry", return_value=FakeChinaXivResp(text=page)):
            with self.assertRaisesRegex(RuntimeError, "未挂载可下载的全文 PDF"):
                dp.resolve_metadata("202410.00098")

    def test_doi_prefix_routes_to_chinaxiv(self):
        with mock.patch.object(dp, "_get_with_retry", return_value=FakeChinaXivResp(text=CHINAXIV_PAGE)) as g:
            meta, pdf_url, arxiv_id = dp.resolve_metadata("10.12074/202410.00098")
        self.assertIsNone(arxiv_id)
        self.assertEqual(meta["doi"], "10.12074/202410.00098")
        # abs 页面请求只发一次（DOI → ID 复用同一解析链）
        self.assertIn("/abs/202410.00098", g.call_args[0][0])

    def test_abs_url_routes_to_chinaxiv(self):
        with mock.patch.object(dp, "_get_with_retry", return_value=FakeChinaXivResp(text=CHINAXIV_PAGE)):
            meta, pdf_url, arxiv_id = dp.resolve_metadata("https://chinaxiv.org/abs/202410.00098")
        self.assertIsNone(arxiv_id)
        self.assertTrue(pdf_url.endswith("&filetype=pdf"))

    def test_download_403_maintenance_raises_explicitly(self):
        maintenance = FakeChinaXivResp(status_code=403, text="<html><title>系统正在维护中</title></html>")
        with mock.patch.object(dp, "_get_with_retry", return_value=maintenance):
            with self.assertRaisesRegex(RuntimeError, "HTTP 403"):
                dp.download_pdf(f"{dp.CHINAXIV_BASE_URL}/user/download.htm?uuid=x&filetype=pdf")

    def test_page_without_cite_string_is_linear_not_catastrophic(self):
        # 性能审查 C-1 回归：站改版/维护页导致的失配场景，大页面必须快速失败而非组合回溯
        big = "<html><body>" + "<p>关键词.更多词.段落内容</p>" * 400 + "</body></html>"  # ~100KB 单行
        with mock.patch.object(dp, "_get_with_retry", return_value=FakeChinaXivResp(text=big)):
            import time
            start = time.monotonic()
            with self.assertRaises(RuntimeError):
                dp.resolve_chinaxiv("202410.00098")
            self.assertLess(time.monotonic() - start, 5.0, "引用串失配出现组合级回溯（C-1 回归）")

    def test_no_fulltext_error_carries_metadata_and_abstract(self):
        # 架构审查 M3 回归：无全文时错误消息必须带上标题/摘要（ChinaXiv 无检索 API，摘要拿不到第二次）
        page = CHINAXIV_PAGE.replace("&filetype=pdf", "")
        with mock.patch.object(dp, "_get_with_retry", return_value=FakeChinaXivResp(text=page)):
            with self.assertRaisesRegex(RuntimeError, "所谓影响关系有待商榷"):
                dp.resolve_chinaxiv("202410.00098")

    def test_403_error_message_strips_ansi_escapes(self):
        # 安全审查 S4 回归：响应体中的 ANSI 转义序列不得进入终端输出
        evil = FakeChinaXivResp(status_code=403, text="<div>\x1b[31m系统正在维护\x1b[0m</div>")
        with mock.patch.object(dp, "_get_with_retry", return_value=evil):
            with self.assertRaises(RuntimeError) as cm:
                dp.download_pdf(f"{dp.CHINAXIV_BASE_URL}/user/download.htm?uuid=x&filetype=pdf")
            self.assertNotIn("\x1b", str(cm.exception))

    def test_http_error_page_raises(self):
        with mock.patch.object(dp, "_get_with_retry", return_value=FakeChinaXivResp(status_code=404, text="")):
            with self.assertRaisesRegex(RuntimeError, "HTTP 404"):
                dp.resolve_chinaxiv("199999.99999")


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
