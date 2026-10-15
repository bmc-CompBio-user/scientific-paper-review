# Scientific paper review

A reproducible local Python workflow for reviewing scientific reasoning in PDF papers and manuscripts with **Ollama `qwen3.5:122b-a10b`, vision, `think=false`**. All model instructions and reports are in English.

The review concentrates on experimental design, causal inference, interpretation versus hypotheses, evidence strength, triangulation, orthogonal validation, and consequential missing validation. It produces a review for human assessment, not an acceptance decision or an automatic scientific quality score.

The intended first cohort is approximately 20 independent studies. Ordinary model mistakes are retained. Human annotations identify material errors recurring across independent studies before a future protocol is changed. There are no Baldi-specific corrections in the production prompts.

## Install

Python **3.11 or newer**, macOS or Linux, and a running local Ollama installation are required. The workflow was locally exercised with Python 3.12. Hardware must support the requested model and context length.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
ollama pull qwen3.5:122b-a10b
python -m unittest discover -s tests -v
```

`requirements.lock` pins runtime dependencies. Python, PyMuPDF and jsonschema versions, package implementation, prompts, settings, PDF hashes, Ollama version and model digest are recorded or checked per run. A fixed seed and temperature improve repeatability but do not guarantee bit-identical model output across hardware or software changes.

## First manuscript and batch

Copy `examples/batch.example.json` to `batch.local.json`, then replace its placeholder paths with local PDFs. Add the main PDF and every supplied supplement as separate document entries. PDF pages are **one-based physical PDF pages**, not printed journal page numbers. Optional method-page hints are manual metadata, not image crops.

```sh
paper-review doctor batch.local.json
paper-review prepare batch.local.json --run-id cohort-01
paper-review run batch.local.json --run-id cohort-01 --max-page-jobs 2
paper-review run batch.local.json --run-id cohort-01
```

The bounded command runs at most two new page jobs across the selected batch. It resumes cached page jobs, and synthesizes a study only when all its supplied PDF pages have completed. Run the same final command again after a pause; completed calls are reused. A failed attempt requires an explicit `--retry-failed`, which creates a new attempt and preserves the old one. A failure in one paper is recorded while other papers continue; the command returns a nonzero exit status if any selected paper fails.

Add about 20 paper entries to the manifest, or append them gradually. Existing entries, source PDFs and protocol settings cannot be changed within a run ID. Use a new run ID for a changed protocol. Different papers sharing experiments or datasets should have the **same `independence_group`**. Mark exploratory development papers with `"exploratory": true` to exclude them from primary recurrence counts.

The local run directory contains `report.md`, `protocol.json`, `provider.json`, `cohort.json`, and per-paper sources, page jobs, review, and operational status. Each attempt preserves the exact request (including image bytes), prompt, response, timing and token metrics, parsed result, quality flags and errors. These logs contain manuscript content and can consume substantial disk space. They remain local and ignored by Git.

## What images and sources mean

PyMuPDF extracts all text blocks and renders each page at 240 DPI, with a full-page overview and four overlapping uniform tiles. **These are not automatically segmented scientific figures.** Text-based figure and caption matches are explicitly unverified candidates; complex layouts, panel boundaries, symbols and reading order can remain ambiguous. No manual figure crops are required.

IDs such as `main.p008.b003` and `supp.p002.img.tile01` map to original document, physical page, text bounding box or image region in `sources.json`. Printed page labels are retained separately. Page jobs receive original text, selected original methods, label-matched caption candidates and the source inventory. The final review receives all page evidence records, selected original methods, additional original text and explicit context omissions. Page-level records are provisional model interpretations. The synthesis does not inspect the original images again.

The review assesses the **published or supplied experimental results**. It does not reanalyze underlying raw data, prove a mechanism, guarantee complete methods retrieval, or guarantee correct figure interpretation. Scanned text has no automatic OCR; low-text pages are flagged and their images are supplied. Embedded attachments and non-PDF external supplements must be supplied separately in an appropriate PDF if they are to be reviewed.

## Human evaluation

Read [the protocol](docs/PROTOCOL.md) and [evaluation guide](docs/EVALUATION.md). Enter human-confirmed errors in a local JSONL file; retain correctly assessed claims separately in your evaluation records. Aggregate with:

```sh
paper-review evaluate data/annotations.jsonl data/runs/cohort-01 --output data/evaluation.json
```

The default recurrence threshold is three independent study groups for a human-confirmed material or major scientific reasoning error family. This is a screening rule for subsequent adjudication, not proof that a model has a systematic defect. Citation-format warnings are secondary and do not trigger this scientific recurrence rule.

## Local data and public Git history

The root Git ignore file is an allowlist: only software, schemas, prompts, documentation, examples, tests and a CI configuration example are included. Manuscripts, grant applications, images, existing exploratory benchmarks, `.venv`, local manifests and run outputs are excluded. Existing `paper_pipeline/` experiments can coexist locally; they are not the production CLI. Review the staged file list before any future public commit. Do not force-add confidential inputs or outputs.

See [operations](docs/OPERATIONS.md) for stepwise troubleshooting and [validation](docs/VALIDATION.md) for the scope of testing. The offline tests use synthetic PDFs and a fake provider; they do not measure scientific accuracy.

The CI configuration is provided as `docs/ci-tests.example.yml`. It is not an active GitHub workflow: the publishing account authorization did not include the `workflow` scope. Activate it later by placing it at `.github/workflows/tests.yml` with an appropriately authorized sign-in.
