#!/usr/bin/env python3
"""Convert arxiv LaTeXML HTML paper to markdown using BeautifulSoup.

Usage:
    python3 html2md.py <html_file> <paper_id> [--output <output.md>] [--meta <abs_html_file>]

Extracts structured content from arxiv's LaTeXML HTML pages,
converting formulas, figures, tables, and sections to markdown.
Use --meta to supply an /abs/ page for complete citation_* frontmatter.
"""

import argparse
import re
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag


def _get_latex(math_el: Tag) -> str:
    """Extract LaTeX from a <math> element: alttext attr or <annotation> child."""
    alttext = (math_el.get("alttext") or "").strip()
    if alttext:
        return alttext
    ann = math_el.find("annotation", encoding="application/x-tex")
    if ann:
        return ann.get_text(strip=True)
    return ""


class ArxivHTML2Markdown:
    """Convert arxiv LaTeXML HTML to markdown using BeautifulSoup + lxml.

    Instead of a flat state machine (the old HTMLParser approach), this uses
    recursive tree walkers that naturally handle nested contexts:
    table cells containing math, bold inside captions, etc.
    """

    SECTION_CLASSES = {
        "ltx_section": 2,
        "ltx_subsection": 3,
        "ltx_subsubsection": 4,
        "ltx_paragraph": 4,
    }

    def __init__(self, paper_id: str):
        self.paper_id = paper_id
        self.meta_data: dict = {}

    # ---- Public API ----

    def convert(self, html: str) -> str:
        """Parse HTML and return full markdown document (frontmatter + body)."""
        soup = BeautifulSoup(html, "lxml")
        self._extract_meta(soup)
        body = self._convert_body(soup)
        return self._frontmatter() + body

    # ---- Meta extraction ----

    def _extract_meta(self, soup: BeautifulSoup) -> None:
        for meta in soup.find_all("meta"):
            name = meta.get("name", "")
            content = meta.get("content", "")
            if not name.startswith("citation_"):
                continue
            key = name.removeprefix("citation_")
            if key == "author":
                self.meta_data.setdefault("authors", []).append(content)
            else:
                self.meta_data[key] = content
        # Fallback: <title> tag
        if not self.meta_data.get("title"):
            title_tag = soup.find("title")
            if title_tag:
                self.meta_data["title"] = title_tag.get_text(strip=True)

    def _frontmatter(self) -> str:
        title = self.meta_data.get("title", "")
        authors = self.meta_data.get("authors", [])
        date = self.meta_data.get("date", "")
        abstract = self.meta_data.get("abstract", "")
        arxiv_id = self.meta_data.get("arxiv_id", self.paper_id)

        return (
            f"---\n"
            f'arxiv_id: "{arxiv_id}"\n'
            f'title: "{title}"\n'
            f"authors: {authors}\n"
            f'date: "{date}"\n'
            f'abstract: "{abstract[:200]}..."\n'
            f'source_url: "https://arxiv.org/abs/{arxiv_id}"\n'
            f"---\n\n"
            f"# {title}\n\n"
            f"**Authors**: {', '.join(authors)}\n"
            f"**Date**: {date}\n"
            f"**arXiv**: [{arxiv_id}](https://arxiv.org/abs/{arxiv_id})\n\n"
            f"---\n\n"
        )

    # ---- Body conversion ----

    def _convert_body(self, soup: BeautifulSoup) -> str:
        """Convert HTML body to markdown, skipping header metadata."""
        content_el = (
            soup.select_one(".ltx_page_main .ltx_page_content article")
            or soup.select_one(".ltx_page_content article")
            or soup.select_one(".ltx_page_main, .ltx_document")
            or soup.find("article")
            or soup.body
            or soup
        )

        self._content_started = False
        parts: list[str] = []

        for child in list(content_el.children):
            if not isinstance(child, Tag):
                continue
            result = self._process_top_level(child)
            if result:
                parts.append(result)

        body = "".join(parts)
        body = re.sub(r"\n{4,}", "\n\n\n", body)
        body = re.sub(r" +\n", "\n", body)
        return body

    def _process_top_level(self, el: Tag):
        """Process a top-level child of the content area. Returns markdown string or None."""
        cls = el.get("class", [])
        tag_id = el.get("id", "")

        if el.name in ("script", "style", "nav", "meta", "link"):
            return None
        if any(c in cls for c in ("ltx_TOC", "ltx_page_navbar", "ltx_page_footer")):
            return None

        is_section = any(c in self.SECTION_CLASSES for c in cls)
        is_abstract = tag_id.startswith("abstract") or tag_id == "abstract"
        is_bibliography = "ltx_bibliography" in cls

        if not self._content_started:
            if is_abstract:
                return self._convert_abstract(el)
            if is_section:
                self._content_started = True
            else:
                return None

        if is_section:
            return self._convert_section(el)
        if is_abstract:
            return self._convert_abstract(el)
        if is_bibliography:
            return self._convert_bibliography(el)
        if "ltx_table" in cls and "ltx_equation" not in cls:
            return self._convert_table(el)
        if "ltx_figure" in cls:
            return self._convert_figure(el)
        if "ltx_equation" in cls:
            return self._convert_equation(el)
        if el.name == "p":
            text = self._convert_inline(el).strip()
            return f"\n{text}\n" if text else ""

        # Appendices, standalone tables, and other blocks
        if el.name in ("div", "figure", "section"):
            inner = ""
            for child in list(el.children):
                if isinstance(child, Tag):
                    result = self._process_top_level(child)
                    if isinstance(result, str):
                        inner += result
            return inner

        return None

    # ---- Block converters ----

    def _convert_section(self, el: Tag) -> str:
        depth = 2
        for cls, d in self.SECTION_CLASSES.items():
            if cls in el.get("class", []):
                depth = d
                break

        parts: list[str] = []
        seen_heading = False

        for child in el.children:
            if not isinstance(child, Tag):
                continue
            if child.name in (
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
            ) and "ltx_title" in child.get("class", []):
                if not seen_heading:
                    title = self._extract_title_text(child)
                    if title:
                        parts.append(f"\n{'#' * depth} {title}\n")
                    seen_heading = True
            else:
                result = self._convert_section_child(child)
                if result:
                    parts.append(result)

        return "".join(parts)

    def _extract_title_text(self, title_el: Tag) -> str:
        parts = []
        for child in title_el.children:
            if isinstance(child, NavigableString):
                parts.append(str(child))
            elif isinstance(child, Tag) and "ltx_tag" not in child.get("class", []):
                parts.append(self._convert_inline(child))
        return "".join(parts).strip()

    def _convert_section_child(self, el: Tag) -> str:
        cls = el.get("class", [])
        tag = el.name

        if tag in ("script", "style", "nav"):
            return ""
        if "ltx_TOC" in cls:
            return ""
        if any(c in self.SECTION_CLASSES for c in cls):
            return self._convert_section(el)

        if tag == "figure":
            if "ltx_table" in cls and "ltx_equation" not in cls:
                return self._convert_table(el)
            if "ltx_figure" in cls:
                return self._convert_figure(el)
        if "ltx_equation" in cls:
            return self._convert_equation(el)
        if tag == "p":
            text = self._convert_inline(el).strip()
            return f"\n{text}\n" if text else ""
        if "ltx_bibliography" in cls:
            return self._convert_bibliography(el)

        # Lists
        if tag in ("ul", "ol"):
            return self._convert_list(el)

        # Unrecognised: recurse into children
        inner = ""
        for child in el.children:
            if isinstance(child, Tag):
                inner += self._convert_section_child(child)
        return inner

    def _convert_abstract(self, el: Tag) -> str:
        p = el.find("p", class_="ltx_p")
        if p:
            text = self._convert_inline(p).strip()
        else:
            text = self._convert_inline(el).strip()
        return f"\n## Abstract\n{text}\n" if text else ""

    def _convert_bibliography(self, el: Tag) -> str:
        items = el.find_all("li", class_="ltx_bibitem")
        if not items:
            return ""
        parts = ["\n## References\n"]
        for i, item in enumerate(items, 1):
            tag_el = item.find(class_="ltx_tag_bibitem")
            if tag_el:
                tag_el.extract()
            text = self._convert_inline(item).strip()
            parts.append(f"{i}. {text}\n")
        return "".join(parts)

    # ---- Figure / Table / Equation ----

    def _convert_figure(self, el: Tag) -> str:
        img = el.find("img", class_="ltx_graphics")
        caption = el.find(class_="ltx_caption")
        src = img.get("src", "") if img else ""
        caption_text = ""
        if caption:
            caption_text = self._convert_inline(caption).strip().replace("\n", " ")
        if src:
            url = f"https://arxiv.org/html/{src}"
            return f"\n![{caption_text}]({url})\n"
        return ""

    def _convert_table(self, el: Tag) -> str:
        rows: list[list[str]] = []
        rowspan_tracker: dict[int, int] = {}  # col -> remaining rows after current
        max_cols = 0

        for tr in el.find_all("tr"):
            cells: list[str] = []
            col_idx = 0

            # Insert empty cells for active rowspans from previous rows
            while rowspan_tracker.get(col_idx, 0) > 0:
                cells.append("")
                col_idx += 1

            for cell in tr.find_all(["td", "th"]):
                text = self._convert_inline(cell).strip().replace("\n", " ")
                colspan = int(cell.get("colspan", 1))
                rowspan = int(cell.get("rowspan", 1))

                for _ in range(colspan):
                    cells.append(text)
                    col_idx += 1

                if rowspan > 1:
                    start_col = col_idx - colspan
                    for c in range(colspan):
                        rowspan_tracker[start_col + c] = rowspan

                # Check if next columns are consumed by rowspans
                while rowspan_tracker.get(col_idx, 0) > 0:
                    cells.append("")
                    col_idx += 1

            # Decrement all rowspan counters for next row
            for col in list(rowspan_tracker.keys()):
                rowspan_tracker[col] -= 1
                if rowspan_tracker[col] <= 0:
                    del rowspan_tracker[col]

            if cells and any(c for c in cells):
                rows.append(cells)
                max_cols = max(max_cols, len(cells))

        if not rows:
            return ""

        # Pad all rows to same column count
        for row in rows:
            while len(row) < max_cols:
                row.append("")

        # Insert header separator if first row contains <th>
        first_tr = el.find("tr")
        if first_tr and first_tr.find(["th"]):
            sep_row = ["---"] * max_cols
            rows.insert(1, sep_row)

        out = "\n"
        for row in rows:
            out += "| " + " | ".join(row) + " |\n"
        out += "\n"
        return out

    def _convert_equation(self, el: Tag) -> str:
        math_el = el.find("math")
        if math_el:
            latex = _get_latex(math_el)
            if latex:
                return f"\n$$\n{latex}\n$$\n"
        return ""

    # ---- Lists ----

    def _convert_list(self, el: Tag) -> str:
        """Convert <ul>/<ol> to markdown bullet/numbered list."""
        is_ordered = el.name == "ol"
        parts = ["\n"]
        for i, li in enumerate(el.find_all("li", recursive=False), 1):
            # Remove ltx_tag spans (bullet markers like •) to avoid duplication
            tag_el = li.find(class_="ltx_tag_item")
            if tag_el:
                tag_el.extract()
            text = self._convert_inline(li).strip()
            if not text:
                continue
            text = re.sub(r"\s+", " ", text)
            if is_ordered:
                parts.append(f"  {i}. {text}\n")
            else:
                parts.append(f"  - {text}\n")
        parts.append("\n")
        return "".join(parts)

    # ---- Inline converter ----

    def _convert_inline(self, el) -> str:
        """Recursively convert inline content to markdown string.

        Handles text, math, bold, italic, citations, and nested combinations.
        The recursive tree walk naturally handles contexts like
        ``<td><span class="ltx_font_bold">48.8<math>...</math></span></td>``
        without special routing.
        """
        if isinstance(el, NavigableString):
            return str(el)

        if not isinstance(el, Tag):
            return ""

        tag = el.name
        cls = el.get("class", [])

        # Math
        if tag == "math":
            latex = _get_latex(el)
            if latex:
                display = el.get("display", "inline")
                if display == "block":
                    return f"\n$$\n{latex}\n$$\n"
                return f"${latex}$"
            return ""

        # Citation link: <a href="#bib.bibN">
        if tag == "a":
            href = el.get("href", "")
            if href.startswith("#bib.bib"):
                num = href.removeprefix("#bib.bib")
                if num.isdigit():
                    return f"[{num}]"
            # Regular link: keep href as plain text
            inner = self._convert_inline_children(el).strip()
            return inner

        # Bold / italic
        if "ltx_font_bold" in cls:
            inner = self._convert_inline_children(el)
            stripped = inner.strip()
            return f"**{stripped}**" if stripped else ""
        if "ltx_font_italic" in cls or tag == "em":
            inner = self._convert_inline_children(el)
            stripped = inner.strip()
            return f"*{stripped}*" if stripped else ""

        # Default: recurse into children
        return self._convert_inline_children(el)

    def _convert_inline_children(self, el) -> str:
        parts = []
        for child in el.children:
            result = self._convert_inline(child)
            parts.append(result)
        return "".join(parts)


# ---- Standalone helpers ----


def load_meta_from_abs(abs_html: str) -> dict:
    """Extract citation_* meta tags from an abs (/abstract/) page HTML."""
    soup = BeautifulSoup(abs_html, "lxml")
    meta: dict = {}
    for m in soup.find_all("meta"):
        name = m.get("name", "")
        content = m.get("content", "")
        if name.startswith("citation_"):
            key = name.removeprefix("citation_")
            if key == "author":
                meta.setdefault("authors", []).append(content)
            else:
                meta[key] = content
    return meta


def _strip_http_headers(content: str) -> str:
    """Strip HTTP response headers if present (from recorded responses)."""
    if content.startswith(("h2 ", "HTTP/")):
        parts = content.split("\n\n", 1)
        if len(parts) == 2:
            return parts[1]
    return content


def convert_file(
    html_path: str,
    paper_id: str,
    output_path: str | None = None,
    meta_source: str | None = None,
) -> str:
    html_content = _strip_http_headers(Path(html_path).read_text(encoding="utf-8"))

    converter = ArxivHTML2Markdown(paper_id)
    md = converter.convert(html_content)

    # Merge meta from abs page if provided (overrides HTML meta)
    if meta_source:
        abs_content = _strip_http_headers(Path(meta_source).read_text(encoding="utf-8"))
        for key, value in load_meta_from_abs(abs_content).items():
            converter.meta_data[key] = value
        # Rebuild with merged meta
        md = converter._frontmatter() + converter._convert_body(
            BeautifulSoup(html_content, "lxml")
        )

    if output_path:
        Path(output_path).write_text(md, encoding="utf-8")
        print(f"Written: {output_path}")

    return md


def main():
    parser = argparse.ArgumentParser(
        description="Convert arxiv LaTeXML HTML to markdown"
    )
    parser.add_argument("html_file", help="Path to HTML file")
    parser.add_argument("paper_id", help="arXiv paper ID (e.g., 2605.28042)")
    parser.add_argument(
        "--meta",
        help="Path to abs page HTML for citation_* meta extraction (supplements HTML paper page)",
    )
    parser.add_argument("--output", "-o", help="Output markdown file path")
    args = parser.parse_args()

    md = convert_file(args.html_file, args.paper_id, args.output, args.meta)

    if not args.output:
        print(md)


if __name__ == "__main__":
    main()
