#!/usr/bin/env python3
"""make_test_pdf.py — generate a synthetic watermarked PDF for testing.

Creates sample_daf.pdf: a page of text (fake Hebrew-ish columns) with two
watermark strips drawn as images — a huge tiled banner and a small caption
strip — mimicking the HebrewBooks.org / Moznaim layout so you can exercise
remove_watermarks.py without touching real copyrighted files.
"""

from __future__ import annotations

import os
import sys

import pymupdf

OUT_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_daf.pdf")


def make(out_path: str = OUT_DEFAULT) -> str:
    doc = pymupdf.open()
    page = doc.new_page(width=624, height=838)  # same size as the real dafs

    # --- fake content: two text columns (the "daf") -------------------------
    words = ["daf", "sugya", "mishnah", "gemara", "rashi", "tosfos", "perek",
             "halacha", "amud", "masseches", "shas", "seif", "kohenes", "brocho"]
    for col, x0 in enumerate((40, 330)):
        y = 40
        for line in range(46):
            import random
            random.seed(col * 100 + line)
            n = random.randint(6, 12)
            text = " ".join(random.choice(words) for _ in range(n))
            page.insert_text((x0, y), text, fontsize=9.5, fontname="helv")
            y += 17

    # --- watermark 1: giant tiled strip (like the 7104x302 one) -------------
    wm = pymupdf.Pixmap(pymupdf.csGRAY, pymupdf.IRect(0, 0, 400, 17))
    wm.clear_with(200)  # mid-gray
    for x in range(0, 400, 80):
        # white blocks as a cheap fake of the tiled logo strip
        wm.set_rect(pymupdf.Rect(x + 4, 2, x + 76, 15), (240,))
    wm_xref = doc.get_new_xref()
    doc.update_object(wm_xref, "<</Type/XObject/Subtype/Image/Width 400/Height 17"
                               "/ColorSpace/DeviceGray/BitsPerComponent 8>>")
    doc.update_stream(wm_xref, wm.samples)
    tiled_target = pymupdf.Rect(40, 300, 584, 324)  # very wide -> aspect 22:1
    page.insert_image(tiled_target, xref=wm_xref, keep_proportion=False)

    # --- watermark 2: small caption strip (like the 1800x97 one) ------------
    cap = pymupdf.Pixmap(pymupdf.csGRAY, pymupdf.IRect(0, 0, 300, 16))
    cap.clear_with(210)
    cap.set_rect(pymupdf.Rect(6, 3, 294, 13), (170,))
    cap_xref = doc.get_new_xref()
    doc.update_object(cap_xref, "<</Type/XObject/Subtype/Image/Width 300/Height 16"
                                 "/ColorSpace/DeviceGray/BitsPerComponent 8>>")
    doc.update_stream(cap_xref, cap.samples)
    cap_target = pymupdf.Rect(140, 80, 500, 96)  # wide-ish
    page.insert_image(cap_target, xref=cap_xref, keep_proportion=False)

    doc.save(out_path, garbage=4, deflate=True)
    doc.close()
    return out_path


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else OUT_DEFAULT
    print(f"wrote {make(out)}")