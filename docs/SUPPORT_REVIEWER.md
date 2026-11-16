# Using the pipeline as a support reviewer (snapshot of rubric 1.8.0)

This page describes the working configuration to use over the coming weeks, what it delivers, how far it can be trusted, and its known limits. It is a snapshot: the prompts, schemas and code of rubric 1.8.0 are frozen per run, and later changes use a new rubric version.

## What it is for

A local second reader that checks the formal aspects of the scientific method in an experimental life-science manuscript: units and replication, controls, statistics and their reporting, scale and model, multiplicity, representation of data. It reads the text and the page images, never sends anything off the machine, and every finding carries quotes from the text that code has checked. It does not judge whether the biology is right and it does not replace the human review. Use each finding as a pointer and check it against the paper before it enters a review.

## Requirements

Apple silicon or a Linux machine with enough memory for `qwen3.5:122b-a10b` (about 83 GB resident with a context of 196,608 tokens), Python 3.11 or newer, Ollama 0.40 or newer. The model needs the whole GPU memory; do not run anything else on it. See README for installation. All 38 tests must pass before use.

## Procedure for one manuscript

1. Put the PDF (and, if you have them, the supplementary PDFs) in a private folder outside the repository. Unpublished manuscripts stay local; keep manifests under `data/manifests/` and outputs under `data/runs/` or `outputs/`, which Git ignores.
2. Drop the reference pages and get suggested method pages: `paper-review trim paper.pdf --out paper_trimmed.pdf --id my-study`. The command prints the dropped pages, the method pages in the numbering of the trimmed file and a manifest entry. Check both against the PDF.
3. Write a manifest with the settings below and the manifest entry (add supplementary PDFs as further documents with their own `method_pages`). An example is in `examples/support-reviewer.example.json`.
4. Run once, without editing any file under `scientific_review/` while it runs and without preparing runs long before they start (the code, prompts and settings are fingerprinted when a run is prepared): `paper-review prepare manifest.json --run-id my-study-1` then `paper-review run manifest.json --run-id my-study-1`. A 25 to 40 page paper takes about 1 to 1.5 hours; a 45 page paper about 2 hours.
5. Read `data/runs/my-study-1/papers/<id>/executive_summary.md` first (write it with `paper-review summary data/runs/my-study-1`), then `report.md` for the details. `scores.json`, `expchecks.json`, `experiments.json` and `crosscheck.json` hold the structured results.

Recommended settings: rubric `scientific-method-v1.8.0`, `num_ctx` 196608, `review_text_chars` 500000 (540000 for papers of 45 pages or more; check the review prompt stays below about 176,000 tokens), `page_num_predict` 8192, `review_num_predict` 20000, `method_text_chars` 64000. Other settings keep their defaults.

Rubric `scientific-method-v1.9.0` is an optional, faster layout (about 25 percent less model time on a 39-page paper) but gives different findings: fewer concerns per experiment, a different experiment inventory and claim set. It has not been validated against the reviewed findings, so keep 1.8.0 for support-reviewer work. See the 1.9.0 entry in `docs/CHANGELOG.md`.

If a run stops: read `status.json` and the failed attempt, fix the cause, and use a new run ID (code changes need a new run ID); `--retry-failed` retries a failed call; `--reuse-completed-from <run>` reuses completed page results of an earlier run of the same paper; `--reuse-also crosscheck,experiments` also reuses those stages.

## What you get

- `executive_summary.md`: four scores from 0 to 5 (5 = few concerns) for evidence strength, experimental design, statistical procedures and reporting, the central claims, the recurring issues, and the scope notes. The scores for design, statistics and reporting are computed from the share of checked experiments with a concern per aspect and from review-level reporting statuses. Evidence strength comes from the review model's claim analysis and is not validated (see below). Treat the scores as a way to compare how much formal reporting is missing, not as a quality grade.
- `report.md`: reading guide with the scope of the search, the recurring issues across experiments (one entry per repeated problem, naming the affected experiments), the remaining concerns by experiment, a separate block of suggestions (scope of conclusions, completeness of controls; rated less reliable), the claim analysis, and the review-level reporting statuses.
- Every absence finding means not stated in the supplied text. Supplementary files that were not supplied, source data and the content of figure panels are not searched, except that concerns about things that usually sit in figures (time points, doses, axes, annotations, data points) are checked against the page image.

## How far to trust it (measured, one rater)

96 findings were rated by the owner of the reviews on two sheets, one with an earlier rubric version.

- Rubric 1.5.0, 60 findings (six papers): 60 percent fully correct, 83 percent correct or partly correct. The weakest part was the cross-check of passages (25 percent fully correct).
- Rubric 1.8.0, 36 findings from four papers that were not in the first sheet: 82 percent fully correct and 91 percent correct or partly correct (3 unsure left out). The cross-check is now restricted to numeric differences and produced almost no items.
- Pooled over both sheets, per-experiment checks and review-level findings without the two judgement aspects: 76 percent fully correct (95 percent interval 65 to 84) and 94 percent correct or partly correct. The target of very high precision is not met yet.
- Strong aspects (all or nearly all correct): unit of inference, uncertainty display, replicate independence, batch and confounding, multiplicity, internal consistency, software and parameters. Weak: scope of conclusions and completeness of controls (shown separately as suggestions), reference normalization, and findings about information that sits in figures or supplements.
- Evidence strength: across seven eLife papers the score shows no relation to eLife's own wording for the strength of evidence. Do not rely on it.
- Revisions of two papers addressed 1 of 64 and 0 of 42 concerns outright and 14 and 4 partly; where they did, they matched what the tool had flagged. This is weak support only.

## Known limits and failure modes

- Text-only stages cannot see figure panels; claims about what a figure shows need the page-image check, which covers only some topics. Information in supplements is invisible unless the supplement is supplied.
- Method-specific practice is not understood well (for example that delta-delta Ct normalization is not a flaw, or that a mutant is compared with wild type in a blocked design).
- Fonts that encode ligatures without a mapping drop letters in some PDFs ("interac ons"); this can hide a statement. Running headers and page numbers are removed, but unusual layouts (two-column with line numbers, scanned pages) need a look at the extracted text.
- The model can still misread a sentence; about one finding in five was not fully correct. The claim ratings in the claim analysis tend to be generous.
- Reports are long. The executive summary and the recurring issues are the short route in.

## Keeping it useful

Keep rating findings from real use (correct, partly correct, incorrect, with the reason) in a private sheet; the rating sheet builders in the development notes show the format. Changes to prompts or code should not be made on a single manuscript; collect recurring errors first and make them a new rubric version.
