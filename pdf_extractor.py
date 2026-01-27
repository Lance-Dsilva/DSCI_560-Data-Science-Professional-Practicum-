#!/usr/bin/env python3


from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional

import pdfplumber







def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def is_likely_header_footer(line: str) -> bool:
    """
    Heuristic: drop page numbers and repeated boilerplate-like lines.

    """
    s = norm_space(line).lower()

    # page numbers / "future of jobs report 2025 17" style
    if re.fullmatch(r"\d+", s):
        return True
    if "future of jobs report" in s and re.search(r"\b\d+\b", s):
        return True
    if s.startswith("january 2025") and "future of jobs report" in s:
        return True

    return False


def merge_hyphenation(prev: str, nxt: str) -> Tuple[str, str, bool]:
    """
    If a line ends with a hyphen and next line starts with a lowercase letter,
    merge: "transfor-" + "mation" => "transformation"
    """
    if prev.endswith("-") and nxt and nxt[0].islower():
        return prev[:-1], nxt, True
    return prev, nxt, False


def should_join_with_space(prev: str, nxt: str) -> bool:
    """
    Decide whether to join lines with a space (same paragraph) vs newline.
    """
    prev_s = prev.rstrip()
    nxt_s = nxt.lstrip()

    if not prev_s:
        return False

    # Bullet / list-like next line
    if re.match(r"^(\u2022|-|–|\*|\d+\.)\s+", nxt_s):
        return False

    # New section / heading-ish
    if re.match(r"^[A-Z][A-Z\s]{3,}$", nxt_s):  # SHOUTY headings
        return False
    if re.match(r"^(figure|table|box)\s+\d", nxt_s.lower()):
        return False

    # If previous ends with sentence punctuation, keep newline more often
    if prev_s.endswith((".", "!", "?", ":")):
        return False

    return True





def split_by_gutter_gap(words_in_row: List[Dict[str, Any]], min_gap: float = 25.0):
    """
    Given words already sorted by x0, split into segments if there's a big x-gap.
    Returns list of segments (each segment is a list of word dicts).
    """
    if not words_in_row:
        return []

    segments = []
    current = [words_in_row[0]]

    for w in words_in_row[1:]:
        prev = current[-1]
        gap = w["x0"] - prev["x1"]
        # Big horizontal gap => likely moved to next column
        if gap >= min_gap:
            segments.append(current)
            current = [w]
        else:
            current.append(w)

    segments.append(current)
    return segments




class Line:
    def __init__(self, y: float, x0: float, x1: float, text: str, kind: str = "single"):
        self.y = y
        self.x0 = x0
        self.x1 = x1
        self.text = text
        self.kind = kind

def words_to_lines(words: List[Dict[str, Any]], y_tol: float = 3.0) -> List[Line]:

    if not words:
        return []

    # Sort words top->bottom then left->right
    words_sorted = sorted(words, key=lambda w: (w["top"], w["x0"]))

    # 1) group into rows by Y
    rows: List[List[Dict[str, Any]]] = []
    current_row: List[Dict[str, Any]] = []
    current_y = words_sorted[0]["top"]

    for w in words_sorted:
        if abs(w["top"] - current_y) <= y_tol:
            current_row.append(w)
        else:
            rows.append(current_row)
            current_row = [w]
            current_y = w["top"]
    if current_row:
        rows.append(current_row)

    # 2) for each row, sort by x and split into segments if there's a gutter gap
    out: List[Line] = []
    for row in rows:
        row_sorted = sorted(row, key=lambda w: w["x0"])


        segments = split_by_gutter_gap(row_sorted, min_gap=25.0)

        for seg in segments:
            text = " ".join(w["text"] for w in seg)
            x0 = min(w["x0"] for w in seg)
            x1 = max(w["x1"] for w in seg)
            y = min(w["top"] for w in seg)
            out.append(Line(y=y, x0=x0, x1=x1, text=norm_space(text), kind="single"))

    return out


def classify_columns(lines: List[Line], page_width: float, gutter_ratio: float = 0.5) -> List[Line]:

    mid = page_width * gutter_ratio
    classified: List[Line] = []

    for ln in lines:
        # If it crosses the mid point, treat as full-width
        if ln.x0 < mid < ln.x1:
            ln.kind = "full"
        else:
            ln.kind = "left" if ln.x1 <= mid else "right"
        classified.append(ln)

    return classified


def reconstruct_page_text(
    page: pdfplumber.page.Page,
    y_tol: float = 3.0,
    drop_headers_footers: bool = True,
    crop_top: float = 0.0,
    crop_bottom: float = 0.0,
) -> Dict[str, Any]:
    """Extract and reconstruct one page into logical reading order."""
    # Optional crop (useful if headers/footers are very consistent)
    bbox = (0, crop_top, page.width, page.height - crop_bottom) if (crop_top or crop_bottom) else None
    p = page.crop(bbox) if bbox else page

    # Extract words with coordinates
    words = p.extract_words(
        keep_blank_chars=False,
        use_text_flow=False,      # we do our own flow
        extra_attrs=[]
    )

    # Convert to lines, then classify columns
    lines = words_to_lines(words, y_tol=y_tol)
    lines = classify_columns(lines, page_width=p.width, gutter_ratio=0.5)

    # Sort in logical order:
    # 1) full width by y
    # 2) left column by y
    # 3) right column by y
    full = sorted([ln for ln in lines if ln.kind == "full"], key=lambda ln: ln.y)
    left = sorted([ln for ln in lines if ln.kind == "left"], key=lambda ln: ln.y)
    right = sorted([ln for ln in lines if ln.kind == "right"], key=lambda ln: ln.y)

    ordered = full + left + right

    # Drop empty and optional header/footer lines
    filtered: List[str] = []
    for ln in ordered:
        if not ln.text:
            continue
        if drop_headers_footers and is_likely_header_footer(ln.text):
            continue
        filtered.append(ln.text)

    # Merge into paragraphs
    out_lines: List[str] = []
    i = 0
    while i < len(filtered):
        cur = filtered[i]
        if not out_lines:
            out_lines.append(cur)
            i += 1
            continue

        prev = out_lines[-1]

        # Hyphen merge
        prev2, cur2, did_merge = merge_hyphenation(prev, cur)
        if did_merge:
            out_lines[-1] = prev2 + cur2  # no space
            i += 1
            continue

        # Join vs newline
        if should_join_with_space(prev, cur):
            out_lines[-1] = prev.rstrip() + " " + cur.lstrip()
        else:
            out_lines.append(cur)
        i += 1

    page_text = "\n".join(out_lines).strip()

    return {
        "page_number": page.page_number,
        "width": page.width,
        "height": page.height,
        "text": page_text,
        "line_count": len(out_lines),
    }


def extract_pdf(
    pdf_path: str,
    out_txt: str,
    out_jsonl: str,
    max_pages: Optional[int] = None,
    y_tol: float = 3.0,
    drop_headers_footers: bool = True,
    crop_top: float = 0.0,
    crop_bottom: float = 0.0,
) -> None:
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        n = min(total, max_pages) if max_pages else total

        all_text_pages: List[str] = []

        with open(out_jsonl, "w", encoding="utf-8") as fj:
            for idx in range(n):
                page = pdf.pages[idx]
                rec = reconstruct_page_text(
                    page,
                    y_tol=y_tol,
                    drop_headers_footers=drop_headers_footers,
                    crop_top=crop_top,
                    crop_bottom=crop_bottom,
                )

                # Save JSONL
                fj.write(json.dumps(rec, ensure_ascii=False) + "\n")

                # Save TXT with clear page breaks
                all_text_pages.append(f"\n\n--- PAGE {rec['page_number']} ---\n\n{rec['text']}")

        with open(out_txt, "w", encoding="utf-8") as ft:
            ft.write("".join(all_text_pages).strip())


# -----------------------------
# CLI
# -----------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Extract logical reading-order text from 2-column PDFs.")
    ap.add_argument("pdf", help="Path to input PDF")
    ap.add_argument("--out", default="output.txt", help="Output text file")
    ap.add_argument("--jsonl", default="output_pages.jsonl", help="Output JSONL file")
    ap.add_argument("--max-pages", type=int, default=None, help="For testing: only process first N pages")
    ap.add_argument("--y-tol", type=float, default=3.0, help="Line grouping tolerance (pixels)")
    ap.add_argument("--keep-headers-footers", action="store_true", help="Do NOT drop header/footer lines")
    ap.add_argument("--crop-top", type=float, default=0.0, help="Crop this many points from top (optional)")
    ap.add_argument("--crop-bottom", type=float, default=0.0, help="Crop this many points from bottom (optional)")
    args = ap.parse_args()

    extract_pdf(
        pdf_path=args.pdf,
        out_txt=args.out,
        out_jsonl=args.jsonl,
        max_pages=args.max_pages,
        y_tol=args.y_tol,
        drop_headers_footers=not args.keep_headers_footers,
        crop_top=args.crop_top,
        crop_bottom=args.crop_bottom,
    )

    print(f"Done.\n- Text:   {args.out}\n- JSONL:  {args.jsonl}")


if __name__ == "__main__":
    main()
