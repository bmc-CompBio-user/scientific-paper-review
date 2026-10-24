"""Page rendering, not semantic figure segmentation. All original blocks survive."""
from pathlib import Path
import re
import pymupdf
from .common import digest, read, write

FIGURE = re.compile(r"\b(?:Figures?|Figs?\.)\s+(S?\d+)(?:[A-H])?", re.I)
CAPTION = re.compile(r"^\s*(?:Figure|Fig\.)\s+(S?\d+)\s*[.:|\u2013\u2014]", re.I)


def role(text, index):
    low = text.lower()
    if CAPTION.search(text):
        return "figure_or_results"
    if len(text.strip()) < 350 and index <= 2:
        return "cover_or_short_page"
    if "key resources table" in low:
        return "resources"
    if re.search(r"\b(method details|statistical analysis|quantification and|star\+methods)\b", low):
        return "methods_candidate"
    # A hint only; multicolumn references and mixed pages cannot be reliably classified by regex.
    if len(re.findall(r"\b(?:19|20)\d{2}\b", text)) >= 15 and "figure" not in low:
        return "references_candidate"
    return "content"


def extract(paper, folder, settings):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / "sources.json"
    identity = [{"id": d["id"], "path": d["path"], "sha256": digest(d["path"]),
                 "method_pages": d.get("method_pages", [])} for d in paper["documents"]]
    if manifest_path.exists():
        old = read(manifest_path)
        if old["documents"] != identity:
            raise ValueError("Input PDF or document configuration changed; choose a new run ID")
        for page in old["pages"]:
            for im in page["images"]:
                if not (folder / im["path"]).exists() or digest(folder / im["path"]) != im["sha256"]:
                    raise ValueError("Cached image missing/changed; restore it or use a new run ID")
        return old
    if (folder / "EXTRACTION_STARTED.json").exists():
        raise ValueError("Incomplete extraction exists; retain it and use a new run ID (no silent overwrite)")
    write(folder / "EXTRACTION_STARTED.json", {"documents": identity})
    result = {"documents": identity, "pages": [], "warnings": [], "pymupdf": pymupdf.__version__,
              "segmentation": "full pages and uniform overlapping tiles; figure/caption links are candidates"}
    for doc in identity:
        with pymupdf.open(doc["path"]) as pdf:
            if pdf.needs_pass:
                raise ValueError("Password-protected PDF: " + doc["id"])
            if any(n < 1 or n > len(pdf) for n in doc["method_pages"]):
                raise ValueError("Method-page hint outside document: " + doc["id"])
            if pdf.embfile_count():
                result["warnings"].append({"document": doc["id"], "kind": "embedded_files_not_extracted",
                    "files": pdf.embfile_names()})
            for n, page in enumerate(pdf, 1):
                prefix = f"{doc['id']}.p{n:03d}"
                blocks = []
                for b in page.get_text("blocks", sort=True):
                    if b[6] == 0 and b[4].strip():
                        blocks.append({"id": f"{prefix}.b{len(blocks):03d}", "text": b[4].strip(), "bbox": list(b[:4])})
                text = "\n\n".join(b["text"] for b in blocks)
                text_path = Path("text") / f"{prefix}.txt"
                (folder / text_path).parent.mkdir(exist_ok=True)
                (folder / text_path).write_text(text, encoding="utf-8")
                hints = []
                for b in blocks:
                    match = CAPTION.match(b["text"])
                    if match:
                        hints.append({"label": "Figure " + match[1].upper(), "source": b["id"],
                                      "caption_start": b["text"][:350], "verified": False})
                rects = [("full", page.rect)]
                if settings["tiles"]:
                    w, h = page.rect.width, page.rect.height
                    for row in range(2):
                        for col in range(2):
                            rects.append((f"tile{row}{col}", pymupdf.Rect(max(0, (col*.5-.04)*w), max(0, (row*.5-.04)*h),
                                min(w, ((col+1)*.5+.04)*w), min(h, ((row+1)*.5+.04)*h))))
                images = []
                for name, rect in rects:
                    image_path = Path("images") / f"{prefix}_{name}.png"
                    (folder / image_path).parent.mkdir(exist_ok=True)
                    pix = page.get_pixmap(dpi=settings["dpi"], clip=rect, alpha=False)
                    pix.save(str(folder / image_path))
                    images.append({"id": f"{prefix}.img.{name}", "path": str(image_path), "sha256": digest(folder/image_path),
                                   "bbox": list(rect), "width": pix.width, "height": pix.height})
                hint = "methods_hint" if n in doc["method_pages"] else role(text, n)
                result["pages"].append({"id": prefix, "document": doc["id"], "pdf_page": n,
                    "page_label": page.get_label(), "role_hint": hint, "blocks": blocks,
                    "text_path": str(text_path), "images": images, "caption_candidates": hints,
                    "figure_mentions": [{"source": b["id"], "label": "Figure " + m[1].upper()} for b in blocks for m in FIGURE.finditer(b["text"])]})
                if len(text.strip()) < 100:
                    result["warnings"].append({"page": prefix, "kind": "little_text_no_ocr", "image_supplied": True})
    write(manifest_path, result)
    return result
