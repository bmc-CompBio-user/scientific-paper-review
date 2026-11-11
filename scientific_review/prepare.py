"""Prepare a manuscript PDF: drop reference pages and suggest the method pages, before the pipeline renders and reads it."""
import json
import re
from pathlib import Path
import pymupdf
from .pdf import role

METHODS = re.compile(r'(?:\d+\.?\s*)?(?:Materials and Methods|Methods|Method details|Experimental procedures|STAR Methods|Methods and Materials)', re.I)
ENDS = re.compile(r'(?:References|Reference list|Data availability|Acknowledg\w+|Figure legends?|Supplementary \w+)', re.I)


def suggest(pdf_path):
    """{'pages': n, 'drop': [reference pages], 'method_pages': [...] in the numbering of the trimmed file}."""
    with pymupdf.open(pdf_path) as pdf:
        texts = [page.get_text() for page in pdf]
    drop = [i + 1 for i, text in enumerate(texts) if role(text, i + 1) == 'references_candidate']
    keep = [i + 1 for i in range(len(texts)) if i + 1 not in drop]
    start = end = None
    for number in keep:
        lines = [line.strip() for line in texts[number - 1].splitlines()]
        if start is None and any(METHODS.fullmatch(line) for line in lines):
            start = number
        elif start is not None and end is None and any(ENDS.fullmatch(line) for line in lines):
            end = number - 1
    method_pages = []
    if start is not None:
        last = end if end is not None and end >= start else min(start + 6, keep[-1])
        method_pages = [n for n in keep if start <= n <= min(last, start + 9)]
    renumber = {old: new for new, old in enumerate(keep, 1)}
    return {'pages': len(texts), 'drop': drop, 'method_pages': [renumber[n] for n in method_pages]}


def trim(pdf_path, out_path):
    plan = suggest(pdf_path)
    with pymupdf.open(pdf_path) as pdf, pymupdf.open() as out:
        for number in range(1, len(pdf) + 1):
            if number not in plan['drop']:
                out.insert_pdf(pdf, from_page=number - 1, to_page=number - 1)
        out.save(out_path)
    return plan


def manifest_entry(paper_id, trimmed, plan):
    return {'id': paper_id, 'title': 'Replace with the manuscript title', 'independence_group': paper_id, 'exploratory': False,
            'documents': [{'id': 'main', 'path': str(Path(trimmed).resolve()), 'method_pages': plan['method_pages'] or [1]}]}
