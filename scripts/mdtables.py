#!/usr/bin/env python3
"""mdtables.py — 共享的 markdown 表格解析（check_pipeline_integrity / check_inventory 复用）。"""


def split_row(line: str) -> list:
    body = line.strip().strip("|")
    return [c.strip() for c in body.split("|")]


def iter_tables(text: str):
    """产出 (表头行 cells, [数据行 cells])；分隔行（---）自动跳过。"""
    table = []
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if line.startswith("|") and line.endswith("|"):
            cells = split_row(line)
            if cells and set("".join(cells)) <= set("-: "):
                continue
            table.append(cells)
        else:
            if table:
                yield table[0], table[1:]
            table = []
    if table:
        yield table[0], table[1:]


def table_rows_after(text: str, heading_pattern: str) -> list:
    """取标题（MULTILINE 正则）之后第一个表格的数据行。"""
    import re

    section = re.search(heading_pattern, text, re.MULTILINE)
    if not section:
        return []
    rows = []
    in_table = False
    for line in text[section.end():].split("\n"):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            in_table = True
            cells = split_row(stripped)
            if cells and set("".join(cells)) <= set("-: "):
                continue
            rows.append(cells)
        elif in_table:
            break
    return rows
