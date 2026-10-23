from pathlib import Path
from urllib.parse import urlparse
import jsonschema
from .common import PACKAGE, RUBRICS, read, safe_id

DEFAULTS = {
    "model": "qwen3.5:122b-a10b", "host": "http://127.0.0.1:11434", "think": False,
    "temperature": 0, "seed": 42, "num_ctx": 65536, "page_num_predict": 2600,
    "review_num_predict": 10000, "dpi": 240, "tiles": True, "timeout_seconds": 1800,
    "page_text_chars": 18000, "method_text_chars": 24000,
    "review_text_chars": 110000, "method_blocks_per_page": 6,
    "rubric": "scientific-method-v1.0.0"
}


def load(path):
    path = Path(path).resolve()
    manifest = read(path)
    jsonschema.validate(manifest, read(PACKAGE / "schemas/manifest.json"))
    settings = {**DEFAULTS, **manifest.get("settings", {})}
    if settings["think"] is not False:
        raise ValueError("This frozen benchmark uses think=false; create a different protocol for thinking models")
    host = urlparse(settings["host"])
    if host.scheme != "http" or host.hostname not in {"127.0.0.1", "localhost", "::1"} or host.username or host.password or host.path not in {"", "/"}:
        raise ValueError("Only a local HTTP Ollama endpoint is supported; manuscripts stay local")
    papers = []
    ids = set()
    for item in manifest["papers"]:
        item = dict(item)
        safe_id(item["id"])
        if item["id"] in ids:
            raise ValueError("Duplicate paper ID: " + item["id"])
        ids.add(item["id"])
        documents = []
        doc_ids = set()
        for doc in item["documents"]:
            safe_id(doc["id"])
            if doc["id"] in doc_ids:
                raise ValueError("Duplicate document ID")
            doc_ids.add(doc["id"])
            pdf = (path.parent / doc["path"]).resolve()
            if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
                raise ValueError("Missing/non-PDF input: " + str(pdf))
            documents.append({**doc, "path": str(pdf)})
        item["documents"] = documents
        papers.append(item)
    if settings["rubric"] not in RUBRICS:
        raise ValueError("Unknown rubric version")
    return {"manifest_path": str(path), "settings": settings, "papers": papers}
