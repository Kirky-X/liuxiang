#!/usr/bin/env python3
"""Convert PDF paper to markdown with image extraction.

Usage:
    python3 pdf2md.py <pdf_file_or_url> [paper_id] [--output <output.md>]

Supports multiple backends (tried in order):
1. pandoc (best quality, preserves some structure) - system install
2. pymupdf (good quality, extracts images) - pip install pymupdf
3. pdfminer.six (good quality, Python native) - pip install pdfminer.six
4. pdftotext from poppler-utils - system install
5. Raw text extraction fallback (ASCII-only, poor quality)

Images are extracted using pymupdf and saved to an images/ directory
next to the output markdown file, referenced via relative paths.

For URLs, downloads PDF first via urllib.
"""

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path


def download_pdf(url: str, dest: Path) -> None:
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) arxiv-skill/1.0"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        dest.write_bytes(resp.read())


def convert_with_pandoc(pdf_path: Path, images_dir: Path | None = None) -> str | None:
    if not shutil.which("pandoc"):
        return None
    cmd = [
        "pandoc", str(pdf_path),
        "-f", "pdf", "-t", "markdown",
        "--wrap=none", "--markdown-headings=atx",
    ]
    if images_dir:
        images_dir.mkdir(parents=True, exist_ok=True)
        cmd.append(f"--extract-media={images_dir.resolve()}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def convert_with_pdfminer(pdf_path: Path) -> str | None:
    """Extract text using pdfminer.six (Python pure, no system deps)."""
    try:
        from pdfminer.high_level import extract_text

        text = extract_text(pdf_path)
        if text.strip():
            return text
    except Exception:
        pass
    return None


def convert_with_pdftotext(pdf_path: Path) -> str | None:
    if not shutil.which("pdftotext"):
        return None
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def extract_pdf_images(pdf_path: Path, images_dir: Path) -> dict[int, list[str]]:
    """Extract embedded images from PDF using pymupdf.

    Returns a dict mapping page number (1-based) to a list of image filenames
    saved in images_dir. Small icons (< 5KB) and duplicate images are skipped.
    """
    import pymupdf

    images_dir.mkdir(parents=True, exist_ok=True)
    page_images: dict[int, list[str]] = {}
    seen_hashes: set[str] = set()

    with pymupdf.open(str(pdf_path)) as doc:
        for page_idx, page in enumerate(doc, 1):
            for img_idx, img_info in enumerate(page.get_images(full=True), 1):
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                    if not base_image:
                        continue
                    image_bytes = base_image["image"]

                    # 跳过小图标（< 5KB 通常是装饰性图标）
                    if len(image_bytes) < 5000:
                        continue

                    # 去重：相同内容的图片只保存一次
                    img_hash = hashlib.md5(image_bytes).hexdigest()[:12]
                    if img_hash in seen_hashes:
                        continue
                    seen_hashes.add(img_hash)

                    ext = base_image.get("ext", "png")
                    filename = f"page{page_idx}_img{img_idx}.{ext}"
                    filepath = images_dir / filename
                    filepath.write_bytes(image_bytes)

                    page_images.setdefault(page_idx, []).append(filename)
                except Exception:
                    continue

    return page_images


def convert_raw_text(pdf_path: Path) -> str:
    try:
        result = subprocess.run(
            ["pdftotext", str(pdf_path), "-"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    raw = pdf_path.read_bytes()
    text_chunks = []
    current = []
    for byte in raw:
        if 32 <= byte <= 126 or byte in (10, 13, 9):
            current.append(chr(byte))
        else:
            if current:
                text_chunks.append("".join(current))
                current = []
    if current:
        text_chunks.append("".join(current))
    return " ".join(text_chunks)


def remove_toc_block(text: str) -> str:
    """Remove PDF table-of-contents block from extracted text.

    Detects TOC structurally by looking for a sustained run of
    numbered-outline entries in the first portion of the document.
    Requires at least 10 consecutive TOC-like lines to fire.
    """
    lines = text.split("\n")
    first_third = max(1, len(lines) // 3)

    def _is_toc_line(s: str) -> bool:
        """True if a non-empty line looks like a PDF TOC entry."""
        # Dot-leader lines (mostly dots)
        dots = s.count(".")
        if dots > 5 and dots / max(len(s), 1) > 0.3:
            return True
        # Standalone section number like "3.2.1"
        if re.match(r"^\d+(\.\d+)+\s*$", s):
            return True
        # Numbered entry like "3.1 Token-level Memory" or "8 Conclusion"
        if re.match(r"^\d+(\.\d+)*\s", s):
            return len(s) < 100
        return False

    i = 0
    while i < min(len(lines), first_third):
        stripped = lines[i].strip()
        if not _is_toc_line(stripped):
            i += 1
            continue

        # Potential TOC block starting here
        start = i
        toc_count = 0
        while i < len(lines):
            s = lines[i].strip()
            if not s:
                i += 1
                continue
            if _is_toc_line(s):
                toc_count += 1
                i += 1
            else:
                break

        if toc_count >= 10:
            # Check if a "Contents" heading sits right before the block
            j = start - 1
            while j >= 0 and not lines[j].strip():
                j -= 1
            if j >= 0 and lines[j].strip().lower().strip("# ") in (
                "contents",
                "table of contents",
            ):
                start = j
            del lines[start:i]
            break
        i = start + 1  # resume after false start

    return "\n".join(lines)


def cleanup_text(text: str) -> str:
    """Remove PDF extraction artifacts: form feeds, standalone page numbers, TOC dot leaders,
    and single-character garbage lines."""
    lines = text.split("\n")
    result = []
    for line in lines:
        line = line.replace("\f", "")
        stripped = line.strip()

        if not stripped:
            continue

        # Standalone page numbers (1-4 digit lines with no other content)
        if stripped.isdigit() and len(stripped) <= 4:
            continue

        # TOC dot leaders (lines of only dots and spaces)
        if all(c in ". " for c in stripped) and len(stripped) > 2:
            continue

        # Single-character garbage (isolated letters/punctuation)
        if len(stripped) == 1:
            continue

        result.append(line)
    return "\n".join(result)


def add_structure_heuristics(text: str) -> str:
    """Add markdown structure heuristics to plain text."""
    lines = text.split("\n")
    output = []
    for line in lines:
        stripped = line.strip()
        if stripped and (
            stripped.startswith("1 ")
            or stripped.startswith("1. ")
            or stripped.startswith("1.1 ")
            or stripped.startswith("Abstract")
            or stripped.startswith("Introduction")
            or stripped.startswith("Conclusion")
            or stripped.startswith("References")
            or stripped.startswith("Acknowledgment")
        ):
            if len(stripped) < 80:
                if stripped.startswith("References"):
                    output.append(f"\n## {stripped}\n")
                elif stripped[0].isdigit() and "." in stripped[:5]:
                    depth = stripped.count(".") + 2
                    depth = min(depth, 4)
                    output.append(f"\n{'#' * depth} {stripped}\n")
                else:
                    output.append(f"\n## {stripped}\n")
                continue
        output.append(line)
    return "\n".join(output)


def build_markdown(paper_id: str, body: str) -> str:
    frontmatter = f"""---
arxiv_id: "{paper_id}"
source_url: "https://arxiv.org/abs/{paper_id}"
conversion: "pdf"
---
"""
    return frontmatter + body


def convert(source: str, paper_id: str, output_path: str | None = None) -> str:
    # 确定输出路径和图片目录
    if output_path:
        out = Path(output_path)
        images_dir = out.parent / "images"
    else:
        out = None
        images_dir = Path(source).parent / "images" if not source.startswith("http") else None

    page_images: dict[int, list[str]] = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / f"{paper_id}.pdf"

        if source.startswith("http"):
            print(f"Downloading PDF from {source}...")
            download_pdf(source, pdf_path)
        else:
            pdf_path = Path(source)

        if not pdf_path.exists():
            print(f"Error: PDF file not found: {pdf_path}", file=sys.stderr)
            sys.exit(1)

        # 优先 pandoc（支持 --extract-media 直接提取图片）
        body = convert_with_pandoc(pdf_path, images_dir)
        if body is None:
            # pymupdf：文本 + 图片提取
            from pymupdf import open as fitz_open
            import logging
            body_parts = []
            with fitz_open(str(pdf_path)) as doc:
                for page_idx, page in enumerate(doc, 1):
                    text = (page.get_text() or "").strip()
                    body_parts.append(text)
            body = "\n\n".join(body_parts)
            if images_dir:
                page_images = extract_pdf_images(pdf_path, images_dir)
        if body is None:
            body = convert_with_pdfminer(pdf_path)
        if body is None:
            body = convert_with_pdftotext(pdf_path)
        if body is None:
            body = convert_raw_text(pdf_path)

        body = cleanup_text(body)
        body = remove_toc_block(body)
        body = add_structure_heuristics(body)

        # 如果图片来自 pymupdf 提取（非 pandoc），在正文后追加图片引用
        if page_images:
            img_lines = []
            for page_num in sorted(page_images):
                for fname in page_images[page_num]:
                    img_lines.append(f"![figure](images/{fname})")
            if img_lines:
                body += "\n\n## 图片\n\n" + "\n\n".join(img_lines)

        md = build_markdown(paper_id, body)

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(f"Written: {out}")
        if images_dir and images_dir.exists():
            img_count = sum(1 for _ in images_dir.iterdir() if _.is_file())
            if img_count:
                print(f"Extracted {img_count} images to {images_dir}/")

    return md


def main():
    parser = argparse.ArgumentParser(description="Convert PDF to markdown with image extraction")
    parser.add_argument("pdf_source", help="Path to PDF file or URL")
    parser.add_argument("paper_id", nargs="?", default=None,
                        help="Paper ID (e.g., 2605.28042). Auto-derived from filename if omitted.")
    parser.add_argument("--output", "-o", help="Output markdown file path")
    args = parser.parse_args()

    # 如果未提供 paper_id，从文件名推导
    paper_id = args.paper_id
    if paper_id is None:
        if args.pdf_source.startswith("http"):
            paper_id = "paper"
        else:
            paper_id = Path(args.pdf_source).stem

    md = convert(args.pdf_source, paper_id, args.output)

    if not args.output:
        print(md)


if __name__ == "__main__":
    main()
