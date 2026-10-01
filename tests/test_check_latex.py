#!/usr/bin/env python3
"""check_latex.py 离线测试：四查逻辑（缺失引用/缺图/重复图/重复章节）+ chktex 解析 + CLI 退出码。

chktex 二进制不测（环境副作用，CI 无 chktex 时走 skipped 路径，已有 skipped 分支测试）。
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import check_latex as cl

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "check_latex.py")


class TestStripComments(unittest.TestCase):
    def test_comment_removed_escape_kept(self):
        tex = "foo % note\nbar \\% baz %tail"
        out = cl.strip_comments(tex)
        self.assertNotIn("note", out)
        self.assertIn("\\%", out)
        self.assertNotIn("tail", out)

    def test_percent_in_url_survives_without_escape(self):
        # 无反斜杠的裸 % 一律按注释处理（LaTeX 语义即如此）
        out = cl.strip_comments("50% off")
        self.assertEqual(out, "50")


class TestCitations(unittest.TestCase):
    BIB = "@article{vaswani2017,\n  title={Attention},\n}\n@inbook{child2020, author={C}}\n@string{conf = {NeurIPS}}\n"

    def test_collect_cited_keys_multi_command(self):
        tex = r"\cite{a,b} \citep[p.~3]{c} \citet{d} \citeyear{e} \citeauthor{f}"
        keys = cl.collect_cited_keys(tex)
        self.assertEqual(keys, ["a", "b", "c", "d", "e", "f"])

    def test_bib_keys_skip_string_comment_preamble(self):
        with tempfile.NamedTemporaryFile("w", suffix=".bib", delete=False) as f:
            f.write(self.BIB)
            path = f.name
        try:
            keys = cl.collect_bib_keys(path)
        finally:
            os.unlink(path)
        self.assertEqual(keys, ["vaswani2017", "child2020"])

    def test_missing_citation_detected(self):
        with tempfile.NamedTemporaryFile("w", suffix=".bib", delete=False) as f:
            f.write(self.BIB)
            path = f.name
        try:
            r = cl.check_missing_citations(r"\cite{vaswani2017} \cite{ghost2024}", [path])
        finally:
            os.unlink(path)
        self.assertEqual(r["severity"], "error")
        self.assertEqual(r["missing_keys"], ["ghost2024"])
        self.assertEqual(r["uncited_bib_entries"], ["child2020"])

    def test_no_bib_file_means_all_cited_missing(self):
        r = cl.check_missing_citations(r"\cite{a}", [])
        self.assertEqual(r["severity"], "error")
        self.assertEqual(r["missing_keys"], ["a"])


class TestFigures(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        with open(os.path.join(self.tmp, "fig1.pdf"), "wb") as f:
            f.write(b"%PDF-")
        with open(os.path.join(self.tmp, "fig2.png"), "wb") as f:
            f.write(b"png")

    def tearDown(self):
        for fn in os.listdir(self.tmp):
            os.unlink(os.path.join(self.tmp, fn))
        os.rmdir(self.tmp)

    def test_missing_figure_detected(self):
        tex = r"\includegraphics{fig1} \includegraphics[width=.5\textwidth]{ghost}"
        r = cl.check_figures(tex, self.tmp)
        self.assertEqual(r["severity"], "error")
        self.assertEqual(r["missing_files"], ["ghost"])

    def test_extensionless_resolution(self):
        tex = r"\includegraphics{fig1} \includegraphics{fig2.png}"
        r = cl.check_figures(tex, self.tmp)
        self.assertEqual(r["severity"], "clean")
        self.assertEqual(r["missing_files"], [])

    def test_duplicate_include_flagged(self):
        tex = r"\includegraphics{fig1} \includegraphics{fig1}"
        r = cl.check_figures(tex, self.tmp)
        self.assertEqual(r["severity"], "warning")
        self.assertEqual(r["duplicate_includes"], ["fig1"])


class TestDuplicateSections(unittest.TestCase):
    def test_same_level_same_title_flagged(self):
        tex = "\\section{Introduction}\n\\section{Methods}\n\\section{Introduction}"
        r = cl.check_duplicate_sections(tex)
        self.assertEqual(r["severity"], "warning")
        self.assertEqual(len(r["duplicates"]), 1)
        self.assertIn("section:introduction", r["duplicates"][0])

    def test_different_level_not_flagged(self):
        tex = "\\section{Setup}\n\\subsection{Setup}"
        r = cl.check_duplicate_sections(tex)
        self.assertEqual(r["severity"], "clean")

    def test_case_and_whitespace_normalized(self):
        tex = "\\section{Data  Collection}\n\\section{data collection}"
        r = cl.check_duplicate_sections(tex)
        self.assertEqual(r["severity"], "warning")

    def test_starred_variant_counts_together(self):
        tex = "\\section{Intro}\n\\section*{Intro}"
        r = cl.check_duplicate_sections(tex)
        self.assertEqual(r["severity"], "warning")


class TestInputPathFence(unittest.TestCase):
    def test_escape_target_rejected(self):
        # 安全审查 S2 回归：\input 的绝对路径/.. 穿越目标必须被拒绝，不得读取项目外文件
        import tempfile as tf
        outside_dir = tf.mkdtemp()
        with open(os.path.join(outside_dir, "secret.tex"), "w", encoding="utf-8") as f:
            f.write("\\cite{leaked}")
        project = tf.mkdtemp()
        try:
            rel = os.path.relpath(os.path.join(outside_dir, "secret.tex"), project)
            with open(os.path.join(project, "main.tex"), "w", encoding="utf-8") as f:
                f.write(f"\\input{{{rel}}}\n\\input{{/etc/passwd}}\n")
            expanded = cl.expand_inputs(os.path.join(project, "main.tex"))
            self.assertNotIn("leaked", expanded)
            self.assertNotIn("cite", expanded)
        finally:
            import shutil
            shutil.rmtree(outside_dir, ignore_errors=True)
            shutil.rmtree(project, ignore_errors=True)

    def test_sibling_input_still_expands(self):
        import tempfile as tf
        project = tf.mkdtemp()
        try:
            with open(os.path.join(project, "main.tex"), "w", encoding="utf-8") as f:
                f.write("\\input{ch1}\n")
            with open(os.path.join(project, "ch1.tex"), "w", encoding="utf-8") as f:
                f.write("OK-CONTENT")
            expanded = cl.expand_inputs(os.path.join(project, "main.tex"))
            self.assertIn("OK-CONTENT", expanded)
        finally:
            import shutil
            shutil.rmtree(project, ignore_errors=True)


class TestChktex(unittest.TestCase):
    def test_not_installed_returns_skipped(self):
        with mock.patch.object(cl.shutil, "which", return_value=None):
            r = cl.run_chktex("x.tex", cl.CHKTEX_DEFAULT_SUPPRESS)
        self.assertEqual(r["severity"], "skipped")

    def test_warning_lines_parsed(self):
        fake = mock.Mock()
        fake.stdout = "Warning 2 in 1, line 14: Command terminated with space.\nWarning 24 in 1, line 20: Wrong index.\n"
        fake.stderr = ""
        with mock.patch.object(cl.shutil, "which", return_value="/usr/bin/chktex"), \
             mock.patch.object(cl.subprocess, "run", return_value=fake):
            r = cl.run_chktex("x.tex", [2, 24, 13, 1])
        self.assertEqual(r["severity"], "warning")
        self.assertEqual(len(r["warnings"]), 2)
        self.assertEqual(r["warnings"][0]["line"], 14)
        # 抑制清单原样记录在结果里
        self.assertEqual(r["suppressed_ids"], [2, 24, 13, 1])


class TestEndToEnd(unittest.TestCase):
    def write_project(self, tex: str, bib: str | None = None):
        tmp = tempfile.mkdtemp()
        with open(os.path.join(tmp, "main.tex"), "w", encoding="utf-8") as f:
            f.write(tex)
        if bib is not None:
            with open(os.path.join(tmp, "refs.bib"), "w", encoding="utf-8") as f:
                f.write(bib)
        return tmp

    def test_clean_project_passes(self):
        tmp = self.write_project(
            "\\documentclass{article}\n\\begin{document}\n\\cite{key1}\n"
            "\\includegraphics{fig}\n\\section{Intro}\n\\end{document}",
            "@article{key1, title={T}}\n",
        )
        with open(os.path.join(tmp, "fig.pdf"), "wb") as f:
            f.write(b"%PDF-")
        r = subprocess.run(
            [sys.executable, "-B", SCRIPT, tmp], capture_output=True, text=True, timeout=60
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("四查全部通过", r.stdout)

    def test_dirty_project_fails_with_findings(self):
        tmp = self.write_project(
            "\\section{A}\n\\section{A}\n\\includegraphics{nope}\n\\cite{missing}",
            "@article{other, title={T}}\n",
        )
        r = subprocess.run(
            [sys.executable, "-B", SCRIPT, tmp], capture_output=True, text=True, timeout=60
        )
        self.assertEqual(r.returncode, 1)
        self.assertIn("missing", r.stdout)
        self.assertIn("nope", r.stdout)

    def test_json_output_shape(self):
        tmp = self.write_project("\\cite{ghost}")
        r = subprocess.run(
            [sys.executable, "-B", SCRIPT, tmp, "--json"], capture_output=True, text=True, timeout=60
        )
        self.assertEqual(r.returncode, 1)
        data = json.loads(r.stdout)
        self.assertFalse(data["clean"])
        checks = {x["check"]: x for x in data["results"]}
        self.assertIn("missing_citations", checks)
        self.assertEqual(checks["missing_citations"]["missing_keys"], ["ghost"])

    def test_input_expansion_reaches_subfile(self):
        tmp = tempfile.mkdtemp()
        with open(os.path.join(tmp, "main.tex"), "w", encoding="utf-8") as f:
            f.write("\\input{ch1}\n")
        with open(os.path.join(tmp, "ch1.tex"), "w", encoding="utf-8") as f:
            f.write("\\cite{need}")
        with open(os.path.join(tmp, "refs.bib"), "w", encoding="utf-8") as f:
            f.write("@article{have, title={T}}\n")
        r = subprocess.run(
            [sys.executable, "-B", SCRIPT, tmp], capture_output=True, text=True, timeout=60
        )
        self.assertEqual(r.returncode, 1)
        self.assertIn("need", r.stdout)

    def test_nonexistent_target_exit_2(self):
        r = subprocess.run(
            [sys.executable, "-B", SCRIPT, "/nonexistent/proj"], capture_output=True, text=True, timeout=60
        )
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
