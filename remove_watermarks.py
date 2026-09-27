#!/usr/bin/env python3
"""remove_watermarks.py — strip watermark images from PDFs while keeping filenames.

Designed for the HebrewBooks.org / Moznaim daf PDFs, but works on any PDF whose
watermarks are drawn as *images* (with or without alpha masks).

Usage:
    python remove_watermarks.py file.pdf [more.pdf ...]      # overwrite in place
    python remove_watermarks.py --out outdir file.pdf ...    # write cleaned copies
    python remove_watermarks.py --interactive file.pdf       # pick images yourself
    python remove_watermarks.py --list file.pdf              # only show images
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass

import pymupdf

try:  # optional: only needed for --show (PNG previews of candidate images)
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False


@dataclass
class Candidate:
    xref: int          # xref of the *painted* image (base, not the smask)
    smask: int         # xref of its alpha mask (0 if none)
    width: int
    height: int
    ext: str
    bbox: pymupdf.Rect  # placement rect on the page; degenerate if not painted
    page: int
    painted: bool       # False when only the smask ref shows a degenerate bbox
    preview: bytes | None = None  # small PNG for --list/--show


def _degenerate(r: pymupdf.Rect) -> bool:
    return r.is_empty or r.is_infinite or (r.width <= 0 and r.height <= 0)


def scan_pdf(path: str, dpi: int = 72) -> list[list[Candidate]]:
    """Return per-page lists of candidate image placements."""
    doc = pymupdf.open(path)
    pages: list[list[Candidate]] = []
    for pno, page in enumerate(doc):
        cands: list[Candidate] = []
        seen: set[int] = set()
        for img in page.get_images(full=True):
            xref, smask = img[0], img[1]
            if xref in seen:
                continue
            seen.add(xref)
            try:
                info = doc.extract_image(xref)
            except Exception:
                continue
            try:
                bbox = page.get_image_bbox(img)
            except Exception:
                bbox = pymupdf.Rect(0, 0, 0, 0)
            painted = not _degenerate(bbox)
            if not painted and smask in seen:
                continue
            seen.add(smask)
            preview = None
            if HAVE_PIL and info["ext"].lower() in ("png", "jpeg", "jpg"):
                try:
                    from io import BytesIO
                    im = Image.open(BytesIO(info["image"]))
                    im.thumbnail((320, 320))
                    buf = BytesIO()
                    im.save(buf, format="PNG")
                    preview = buf.getvalue()
                except Exception:
                    preview = None
            cands.append(Candidate(
                xref=xref, smask=smask, width=info["width"], height=info["height"],
                ext=info["ext"], bbox=bbox, page=pno, painted=painted, preview=preview,
            ))
        pages.append(cands)
    doc.close()
    return pages


def print_listing(path: str, pages: list[list[Candidate]], save_previews: str | None = None) -> None:
    print(f"\n{os.path.basename(path)}:")
    if save_previews:
        os.makedirs(save_previews, exist_ok=True)
    for cands in pages:
        if not cands:
            print(f"  page {cands and ''}-- no images")
            continue
        for c in cands:
            flag = "painted " if c.painted else "smask-only"
            print(f"  page {c.page}: xref={c.xref} smask={c.smask} "
                  f"{c.width}x{c.height} {c.ext} {flag} bbox={c.bbox}")
            if save_previews and c.preview:
                fn = os.path.join(save_previews,
                                  f"p{c.page}_xref{c.xref}.png")
                with open(fn, "wb") as f:
                    f.write(c.preview)


def heuristic_targets(cands: list[Candidate]) -> list[int]:
    """Pick xrefs that look like watermark strips.

    Watermarks on these dafs are extremely wide decorative strips. We flag
    painted images whose aspect ratio is extreme (very wide or very tall) or
    that are unusually large relative to the page. Content scans of text pages
    are usually near the page aspect ratio, so they are not flagged.
    """
    targets = []
    for c in cands:
        if not c.painted:
            continue
        ar = c.width / max(c.height, 1)
        if ar >= 8 or ar <= 0.125:
            targets.append(c.xref)
        elif c.width >= 2000 or c.height >= 2000:
            targets.append(c.xref)
    return targets


def choose_interactively(pages: list[list[Candidate]]) -> list[int]:
    """Prompt per image: [y]es / [n]o / [a]ll painted / [q]uit."""
    import base64
    picked: list[int] = []
    for cands in pages:
        for c in cands:
            print(f"\n  page {c.page}: xref={c.xref} smask={c.smask} "
                  f"{c.width}x{c.height} {c.ext} "
                  f"{'painted' if c.painted else 'smask-only (skip)'} bbox={c.bbox}")
            if not c.painted:
                continue
            if c.preview and HAVE_PIL:
                from io import BytesIO
                Image.open(BytesIO(c.preview)).show(title=f"page {c.page} xref {c.xref}")
            while True:
                ans = input("    remove this image? [y/N/a(q=quit)] ").strip().lower()
                if ans in ("y", "yes"):
                    picked.append(c.xref)
                    break
                if ans in ("n", "no", ""):
                    break
                if ans == "a":
                    picked.extend(x for cc in cands if cc.painted for x in (cc.xref,) if x not in picked)
                    return picked
                if ans in ("q", "quit"):
                    return picked
    return picked


def clean_pdf(path: str, out_path: str, targets: list[int]) -> tuple[int, int]:
    """Delete the target xrefs from every page, save to out_path."""
    tset = set(targets)
    doc = pymupdf.open(path)
    removed = 0
    for page in doc:
        for img in page.get_images(full=True):
            if img[0] in tset:
                try:
                    page.delete_image(img[0])
                    removed += 1
                except Exception as e:
                    print(f"    ! could not delete xref {img[0]}: {e}", file=sys.stderr)
    tmp = out_path + ".tmp"
    doc.save(tmp, garbage=4, deflate=True, clean=True)
    doc.close()
    os.replace(tmp, out_path)
    return removed, len(tset)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Remove watermark images from PDFs, saving under the same name.")
    ap.add_argument("pdfs", nargs="+", help="PDF files to clean")
    ap.add_argument("--out", help="output directory (default: overwrite in place)")
    ap.add_argument("--list", action="store_true", help="only list images, do not modify")
    ap.add_argument("--previews", metavar="DIR",
                    help="save PNG previews of listed images to DIR (needs --list)")
    ap.add_argument("--interactive", action="store_true",
                    help="choose which images to remove yourself (shows each one)")
    ap.add_argument("--xrefs", type=int, nargs="+", default=None,
                    help="explicit xref list to remove (from --list output)")
    args = ap.parse_args()

    if not HAVE_PIL and args.interactive:
        print("note: install Pillow for image previews in --interactive mode", file=sys.stderr)

    rc = 0
    for path in args.pdfs:
        if not os.path.isfile(path):
            print(f"not found: {path}", file=sys.stderr)
            rc = 1
            continue
        try:
            pages = scan_pdf(path)
        except Exception as e:
            print(f"cannot open {path}: {e}", file=sys.stderr)
            rc = 1
            continue

        if args.list:
            print_listing(path, pages, save_previews=args.previews)
            continue

        if args.xrefs is not None:
            targets = args.xrefs
        elif args.interactive:
            targets = choose_interactively(pages)
        else:
            targets = heuristic_targets(pages[0]) if len(pages) == 1 else \
                [x for cands in pages for x in heuristic_targets(cands)]

        if not targets:
            print(f"{os.path.basename(path)}: no watermark-like images detected — "
                  f"skipping (use --list/--interactive/--xrefs)")
            continue

        out = os.path.join(args.out, os.path.basename(path)) if args.out else path
        if args.out:
            os.makedirs(args.out, exist_ok=True)
        try:
            removed, wanted = clean_pdf(path, out, targets)
        except Exception as e:
            print(f"failed cleaning {path}: {e}", file=sys.stderr)
            rc = 1
            continue
        mode = "in place" if out == path else f"to {out}"
        print(f"{os.path.basename(path)}: removed {removed}/{wanted} image xrefs "
              f"({mode}), {os.path.getsize(out) // 1024} KB")

    return rc


if __name__ == "__main__":
    sys.exit(main())