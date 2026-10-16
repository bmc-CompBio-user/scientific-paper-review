# Operations and stepwise troubleshooting

## Routine batch operation

Keep manuscript PDFs and all supplements locally. Add one manifest entry per study with stable IDs and independence groups. Source paths are relative to the manifest, or absolute local paths. Run `doctor`, then `prepare`, then a bounded `run` before a larger batch. Review source coverage and a few original pages manually. Continue the same run without a page limit once the operational checks are satisfactory.

A batch processes papers and pages sequentially to avoid competing for model memory. Use `--paper study-001` to select a paper, repeat for several IDs. Appending new entries is allowed; removing or modifying old entries is rejected. Run locks prevent concurrent writers to the same run directory. SIGINT/process interruption can leave a running attempt; retry creates a new attempt. An interrupted extraction requires a new run ID, preserving partial files for diagnosis.

The software does not launch a persistent service or automatically schedule runs. Keep a terminal session active for long batches. Store local run artifacts on a disk with sufficient space, and back up them separately if needed. A request contains Base64 image bytes, so disk use exceeds the rendered PNG size.

## Troubleshoot one issue at a time

1. **Preflight fails:** inspect the exact error. Confirm Python version, input paths and a running local Ollama service. `paper-review doctor batch.local.json` checks the requested model tag and records its digest; it does not download the model or change the server. Only loopback HTTP is supported and HTTP proxies are disabled.
2. **Source extraction fails:** inspect the paper status and `sources/EXTRACTION_STARTED.json`. Check password protection, malformed PDFs, method-page ranges or storage. Fix the underlying problem and start a new run ID. Do not overwrite retained partial artifacts.
3. **A call times out or truncates:** inspect its `state.json`, exact request and saved response if present. Do not change multiple settings at once. An explicit retry preserves the failed attempt. A changed token/context budget requires a new run ID, keeping the comparison traceable.
4. **Context is too large:** inspect omitted block IDs and the mandatory-context error. Reduce the source package only if a document was genuinely unrelated, or increase the relevant context and character budgets under a new protocol. Do not label omitted methods as absent from the study. Very long source packages may need a future hierarchical synthesis extension.
5. **JSON/schema failure:** the raw response remains available. Retry explicitly once if appropriate. Repeated structural failures across unrelated inputs justify a separate protocol investigation. No repair model silently rewrites responses.
6. **Source ID or claim-link warning:** inspect `quality_flags.json` and original coordinates. Determine whether the error changes a scientific inference. Keep cosmetic source-format issues separate from scientific reasoning failures.
7. **Scientifically questionable review:** compare with original figures, legends and methods; annotate the reasoning error and its consequence. Do not patch the prompt around one manuscript. Examine recurrence after independent studies.

## Reproduce or compare

Keep `protocol.json`, `provider.json`, `cohort.json`, input PDFs and their hashes, source inventory, all attempts and human annotations. Reinstall pinned runtime dependencies and use the recorded Python and Ollama versions/model digest. Model tags can be updated by Ollama; the workflow rejects a changed version/digest in an existing run.

A completed stage is cached, so rerunning it demonstrates resume behavior rather than independent stochastic replication. For an independent repeat, use a different run ID with the same protocol. Never edit successful attempt files in place; put human notes in a separate annotation file.

## Public repository

Before any commit inspect `git status` and `git diff --cached --stat`. The root allowlist excludes manuscripts and local results by default. Keep examples synthetic and path-neutral. Do not force-add local PDFs, model requests, old benchmark outputs or grant files. Git history cannot serve as a backup of excluded local data.

## Primary implementation references

- [Ollama API definitions](https://github.com/ollama/ollama/blob/main/docs/openapi.yaml)
- [Ollama structured outputs](https://github.com/ollama/ollama/blob/main/docs/capabilities/structured-outputs.mdx)
- [PyMuPDF page extraction and rendering](https://pymupdf.readthedocs.io/en/latest/page.html)
- [PyMuPDF image recipes](https://pymupdf.readthedocs.io/en/latest/recipes-images.html)

## Explicit operational recovery

If a new protocol changes only generation ceilings or citation-list ceilings, previously completed page calls can be imported explicitly into a new run:

```sh
paper-review run batch-recovery.local.json --run-id recovery-01 --reuse-completed-from data/runs/original-01
```

The new manifest must point to the same scientific source package. Each imported call is checked against the current scientific prompt, images, source IDs, model identity and options; only output ceilings and citation-list ceilings may differ. Original requests and generation settings are retained and marked with `reuse.json` and `reuse_verified.json`. The imported result is checked against its saved raw response. A changed scientific input, different model, reduced output ceiling, tampered response or incompatible schema rejects reuse. Failed attempts remain at the original run; the new run generates those stages afresh. A fresh final synthesis is always performed.

This is an explicitly composite recovery run, not a homogeneous independent repeat under the new protocol. Preserve the reuse plan and per-call provenance when comparing benchmark results. Ordinary same-protocol retries continue to use `--retry-failed`.
