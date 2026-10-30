#!/usr/bin/env python3

import io
import re
import sys

def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
    text = text.replace("&laquo;", "«").replace("&raquo;", "»").replace("&#039;", "'")
    return " ".join(text.split())

def _tables(html):
    return re.findall(r"<table[^>]*>.*?</table>", html, re.S)

def _rows(table):
    out = []
    for tr in re.findall(r"<tr[^>]*>.*?</tr>", table, re.S):
        cells = re.findall(r"<t[dh][^>]*>.*?</t[dh]>", tr, re.S)
        if cells:
            out.append(cells)
    return out

def parse_card(html):
    
    body = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    sections = []

    
    parts = re.split(r"<h3[^>]*>(.*?)</h3>", body, flags=re.S)
    for i in range(1, len(parts), 2):
        title = clean(parts[i])
        chunk = parts[i + 1] if i + 1 < len(parts) else ""
        rows = []
        for table in _tables(chunk):
            for cells in _rows(table):
                if len(cells) >= 2:
                    rows.append((clean(cells[0]), clean(cells[1])))
        if rows:
            sections.append({"title": title, "rows": rows})

    if not sections:
        
        rows = []
        for table in _tables(body):
            for cells in _rows(table):
                if len(cells) >= 2:
                    rows.append((clean(cells[0]), clean(cells[1])))
        if rows:
            sections.append({"title": "Сведения", "rows": rows})

    return {"sections": sections}

def parse_list(html):
    
    body = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    tables = _tables(body)
    if not tables:
        return {"columns": [], "items": [], "pages": 1, "total": 0}

    table = max(tables, key=len)

    columns = []
    head = re.search(r"<thead[^>]*>.*?</thead>", table, re.S)
    if head:
        for th in re.findall(r"<th[^>]*>(.*?)</th>", head.group(0), re.S):
            columns.append(clean(th))

    items = []
    tbody = re.search(r"<tbody[^>]*>(.*?)</tbody>", table, re.S)
    rows_html = tbody.group(1) if tbody else table
    for tr in re.findall(r"<tr[^>]*>.*?</tr>", rows_html, re.S):
        cells = re.findall(r"<td[^>]*>.*?</td>", tr, re.S)
        if not cells:
            continue
        texts = []
        for cell in cells:
            text = clean(cell)
            if not text and 'class="fas fa-check"' in cell:
                text = "✓"      
            texts.append(text)
        link = re.search(r'href="([^"]*/cm/results/[^"]+)"', tr)
        rid = re.search(r'id="item_([^"]+)"', tr)
        items.append({
            "cells": texts,
            "url": link.group(1) if link else "",
            "id": rid.group(1) if rid else "",
        })

    
    pages = 1
    for m in re.findall(r"[?&]page(?:Number)?=(\d+)", body):
        pages = max(pages, int(m))

    total = 0
    m = re.search(r"<span>\s*\d+\s*-\s*\d+\s*из\s*([\d\s\u00a0]+)\s*</span>", body)
    if m:
        digits = re.sub(r"\D", "", m.group(1))
        total = int(digits) if digits else 0

    return {"columns": columns, "items": items, "pages": pages, "total": total}

def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(argv) < 3:
        print("usage: python pov.py list <file.html> | python pov.py card <file.html>")
        return
    mode, path = argv[1], argv[2]
    with io.open(path, encoding="utf-8", errors="replace") as f:
        html = f.read()

    if mode == "card":
        data = parse_card(html)
        for section in data["sections"]:
            print("\n## %s" % section["title"])
            for label, value in section["rows"]:
                print("   %-55s %s" % (label, value))
    else:
        data = parse_list(html)
        print("колонок: %d, строк: %d, страниц: %d, всего: %s"
              % (len(data["columns"]), len(data["items"]), data["pages"], data["total"]))
        print("колонки:", " | ".join(data["columns"]))
        for item in data["items"][:3]:
            print("  ", " | ".join(item["cells"])[:200], "->", item["url"])

if __name__ == "__main__":
    main(sys.argv)
