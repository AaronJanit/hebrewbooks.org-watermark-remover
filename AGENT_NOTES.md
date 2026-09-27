# Remove Watermarks from PDFs — AI Agent Instructions

How to strip watermark images from the daf PDFs in this folder (`remove-watermarks`) while keeping the same filenames.

## Context
PDFs in this folder (e.g. `daf.pdf`, `daf2.pdf`, `daf3.pdf`) are single-page Hebrew daf scans/text from HebrewBooks.org / Moznaim. Each page contains **2 watermark images** (plus their alpha masks = 4 xrefs):

1. A giant tiled gray **"SHAS MOZNAM"** overlay strip (7104×302 PNG, with an smask)
2. A smaller **"HebrewBooks.org ©Moznaim Publishers. No commercial use allowed."** banner strip (1800×97 PNG, with an smask)

Everything else on the page is real content (text + fonts) — must not be touched.

## Environment
- No venv in this folder. Reuse the one from the background-remover project:
  `C:\Users\Family Janit\Documents\background-remover\.venv\Scripts\python.exe`
- Install PyMuPDF if missing (behind the Techloq TLS filter, must pass the exported CA):
  ```powershell
  $env:SSL_CERT_FILE = "$env:USERPROFILE\Documents\background-remover\techloq-ca.pem"
  & "$env:USERPROFILE\Documents\background-remover\.venv\Scripts\python.exe" -m pip install pymupdf --cert $env:SSL_CERT_FILE --only-binary :all:
  ```
- Set `$env:PYTHONIOENCODING="utf-8"` before running (Hebrew text output crashes cp1252 otherwise).
- Use `import pymupdf` (not the deprecated `import fitz`).

## Procedure
1. **Inspect first — never assume.** List images per page and their bboxes:
   ```python
   import pymupdf
   doc = pymupdf.open(path)
   for img in page.get_images(full=True):
       print(img[0], doc.extract_image(img[0])['width'], doc.extract_image(img[0])['height'],
             page.get_image_bbox(img))
   ```
   Watermark images here show up as very wide/odd aspect strips (7104×302, 1800×97) with real bboxes. The smask partner xref has a degenerate bbox like `Rect(1.0, 1.0, -1.0, -1.0)` — it is only the alpha mask, don't delete it separately.
2. **Verify visually** before deleting: render the page (`page.get_pixmap(dpi=100).save(...)`) and extract the candidate image xrefs — confirm they are watermarks, not content (e.g. a page scan image that just happens to be wide).
3. **Delete the painted (base) image xrefs only**:
   ```python
   page.delete_image(xref)
   ```
   `delete_image` removes the drawing operation and neutralizes the xref; the paired smask is handled automatically. Deleting only the smask xref does nothing.
4. **Save in place via a temp file then `os.replace`** (PDF can't save over itself while open):
   ```python
   doc.save(path + ".tmp", garbage=4, deflate=True, clean=True)
   doc.close()
   os.replace(tmp, path)
   ```
   - `garbage=4` dedupes + removes unreferenced objects (drops the orphaned watermark image data)
   - `clean=True` rewrites content streams
   - After deletion each page may still list ~2 tiny 1×1 image refs (empty placeholders) — that's expected and harmless.
5. **Verify after**: re-render the page to PNG and visually confirm the watermark is gone and content is intact. Text layer and page size should be unchanged.

## Gotchas
- `delete_image` on a page where the image appears multiple times removes it everywhere on that page.
- Do NOT use `doc.del_xml_metadata` or blanket `delete all images` — only the identified watermark xrefs.
- Some PDFs have watermarks as **annotations (stamp)** or **form XObjects** instead of images; check `page.annots()` and `page.get_xobjects()` if `get_images()` doesn't reveal anything. For annotation watermarks use `page.delete_annot(annot)`.
- PowerShell prints native stderr as noisy `NativeCommandError` blocks — harmless for Python warnings; don't confuse with real failures.
- Cleanup afterwards: delete any temp scripts and preview folders so this folder contains only the PDFs and this .md file.