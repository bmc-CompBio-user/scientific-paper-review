# Validation of production v1

Validated locally on 15 October 2026 using Python 3.12.14, PyMuPDF 1.26.5, jsonschema 4.25.1, Ollama 0.40.4 and `qwen3.5:122b-a10b` with `think=false`.

## Offline tests

Nine automated tests pass. They exercise multiple-document source identity and image integrity, local-only/non-thinking configuration, frozen-protocol and append-only cohort checks, response reuse, retained citation warnings, preserved timeout/truncation/JSON failures with explicit retries, a complete mocked page-to-study workflow with bounded pause/resume, context overflow handling, independent-study recurrence counting, and dynamic citation constraints/claim-link warnings.

The provided CI configuration example runs these tests on Python 3.12 with synthetic PDFs and a fake provider. It does not call Ollama and does not evaluate scientific accuracy. GitHub CI is not active: publication of an actual workflow was rejected because the OAuth sign-in lacks the workflow scope. Local test results are reported here; no hosted CI result is claimed.

## Live bounded end-to-end test

A synthetic two-page fixture was processed through the actual local Ollama service: one page with a schematic bar plot and experimental descriptions, and one methods page. Both page calls used a 240 DPI overview plus four overlapping tiles, original methods, source IDs and structured output. A final text-only whole-study review completed.

| Stage | Wall time | Input tokens | Output tokens |
| --- | ---: | ---: | ---: |
| Page 1 vision | 39.9 s | 7,118 | 627 |
| Page 2 vision | 13.1 s | 7,138 | 133 |
| Whole-study synthesis | 58.8 s | 2,406 | 2,907 |

All three responses ended normally, parsed against the structural schemas, and had no mechanical source/claim-link warnings. Total model-call wall time was approximately 112 seconds, including a model load on the first call. Exact prompts, Base64-containing requests, raw responses, token timings and result files are preserved locally and excluded from the public repository.

This establishes operational integration, not scientific validity. The fixture intentionally has incomplete visual data and explicitly identifies itself as synthetic. The model recognized this limitation. Its review also contains questionable reasoning, including treating an explicit direct-regulation hypothesis as an overinterpretation in parts of its assessment and simplistic significance language. These outputs were retained; no paper-specific prompt repair was made. Human evaluation across independent real manuscripts remains necessary.

To reproduce the synthetic operational test from a clean checkout:

```sh
python examples/create_smoke_fixture.py
paper-review run data/smoke/batch.json --run-id synthetic-01
paper-review run data/smoke/batch.json --run-id synthetic-01
```

The second command repetition should reuse the three completed attempts. A local resume check on the tested fixture confirmed zero new page jobs and exactly three retained attempt directories. If the fixture already exists, the helper refuses to overwrite it.

## Scope

A production evaluation across approximately 20 independent real manuscripts has not yet been completed. Scientific accuracy requires human assessment across that cohort.

For new papers, first inspect the preparation manifest and run a bounded few-page test. Verify original legend/method retrieval and image readability before scaling. No test establishes perfect figure segmentation, exhaustive retrieval, universal context-length support, or correct causal interpretation.
