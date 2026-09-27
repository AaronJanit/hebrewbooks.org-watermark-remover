# remove-watermarks
## Fully working AI generated project to remove watermarks from hebrewbooks.org dappim

Remove watermark images from PDFs (HebrewBooks.org / Moznaim daf-style pages)
while keeping the text, fonts, layout and filenames untouched.

The tool finds watermark images — wide decorative strips like a tiled
publisher banner or a "No commercial use allowed" caption — deletes them from
the page content, and re-saves the PDF compactly. Content images (page scans,
photos) are left alone because their aspect ratio doesn't match the watermark
pattern.

> ⚠️ **Legal note:** watermarks often indicate copyright. Only remove them
> from files you have the right to modify, and respect the publisher's terms
> (e.g. Moznaim allows personal/non-commercial use — the watermark says so).

## Install

```bash
pip install -r requirements.txt
```

(Just `pymupdf` is required; `Pillow` adds image previews.)

## Quick start

```bash
# Try it on the bundled real samples (Bechoros daf 9b, HebrewBooks ID# 36081):
python remove_watermarks.py original_watermarked.pdf --list --previews previews
python remove_watermarks.py original_watermarked.pdf --out out

# Or generate a synthetic test PDF and clean it:
python make_test_pdf.py
python remove_watermarks.py sample_daf.pdf
```

## Cleaning your own PDFs

```bash
# 1) Inspect first — see what images are on each page:
python remove_watermarks.py daf.pdf --list --previews previews

# 2) Clean automatically (heuristic: flags extreme-aspect / huge images):
python remove_watermarks.py daf.pdf daf2.pdf daf3.pdf

# 3) Or pick exactly which images to remove (shows each one):
python remove_watermarks.py --interactive daf.pdf

# 4) Or pass the xrefs you saw in --list output:
python remove_watermarks.py --xrefs 60 63 daf.pdf

# Save to a different folder instead of overwriting:
python remove_watermarks.py --out clean daf.pdf
```

The heuristic assumes watermarks are *painted images* with an extreme aspect
ratio (≥ 8:1 or 1:8) or ≥ 2000 px on a side. If your PDF has watermarks drawn
differently (vector graphics, annotations), use `--list` + `--interactive` to
target them manually — see `AGENT_NOTES.md` for the full decision tree,
including annotation stamps and form XObjects.

## How it works

1. `page.get_images(full=True)` lists every image xref per page; each painted
   image has a real bbox, its alpha-mask (`smask`) partner has a degenerate
   one.
2. `page.delete_image(xref)` removes the draw operation (the smask goes with
   it).
3. The document is saved with `garbage=4, deflate=True, clean=True`, which
   drops the now-orphaned image data — that's where the size savings come
   from.
4. Two tiny 1×1 placeholder refs may remain per page afterwards; they are
   harmless.

## Files

| File | Purpose |
|------|---------|
| `remove_watermarks.py` | CLI: scan, list, heuristically clean, interactive pick |
| `make_test_pdf.py` | Generates `sample_daf.pdf` (fake watermarks) for testing |
| `original_watermarked.pdf` | **Sample WITH watermarks** — real daf (Bechoros 9b) as served by HebrewBooks.org: tiled SHAS MOZNAM overlay + HebrewBooks/Moznaim caption strip |
| `sample_daf_clean.pdf` | **Sample WITHOUT watermarks** — the same page after running `remove_watermarks.py original_watermarked.pdf` |
| `AGENT_NOTES.md` | Detailed agent-facing procedure & gotchas |
| `daf*.pdf` | Example cleaned PDFs |

The sample page is **מסכת בכורות דף ט עמוד ב** (Maseches Bechoros, daf 9b) from the
Moznaim Shas, provided on HebrewBooks.org "with their kind permission"
(© Moznaim Publishers — ח. וגשל). It is included here solely to demonstrate
the watermark removal; the same non-commercial-use terms apply.

## License

MIT — see [LICENSE](LICENSE).
