# Changes

## Length caps and one retry for cross-check, inventory and per-experiment checks

A cross-check response ran to the token limit when the model repeated a phrase inside one explanation field, and the experiment inventory of a long paper reached its 16000-token ceiling. Free-text fields of the crosscheck, experiments and expcheck schemas are now length-capped when the request is built (explanation 900 characters, consequence 400, quote 300, topic and label 200, other text 700, strings inside lists 300), which Ollama's constrained decoding honours. A stop at the token limit in these three stages is retried once with a repetition penalty of 1.1; both responses are kept in the attempt folder (`response_length_stop.json`, `request_retry.json`). The default `experiments_num_predict` is now 32000. The review stage is unchanged. The implementation fingerprint changed; use new run IDs.

## Rubric 1.4.0 (prototype, opt-in)

Adds an experiment-inventory stage between the cross-check and the review. A text-only call over the original text lists up to 40 individual experiments with the question or hypothesis and its stated timing, the endpoint and measurement principle, groups and conditions, replicate unit and reported N, representativity (example versus quantified, stated repeats), the controls mentioned and the alternative each addresses, expected controls not mentioned in the supplied text, the statistics and the unit treated as N, and information not stated. Evidence quotes are checked by code against the cited page (`quote_verified`). The inventory is written to `experiments.json`, shown in the report, and passed to the review, which rates claims against the experiments that serve them. Otherwise identical to 1.3.0. New settings `experiments_num_predict` and `experiments_text_chars`. Quote checking also ignores trailing punctuation and, for the inventory, accepts a quote anywhere on the cited block's page. Prototype status: evaluated only by inspecting inventories on cases already reviewed; no end-to-end comparison yet.

## Cross-check post-processing (rubrics 1.2.0 and later)

Cross-check items whose own explanation says the passages agree (for example 'No conflict found' or 'Consistent', or a consequence starting with 'None') are marked `declared_consistent` in `crosscheck.json`, kept there, and left out of the review prompt and the report except for a count. This is a deterministic text rule and does not depend on the prompt, which did not remove the mislabelling in two further cases. Explanations containing 'however', 'but', 'although', 'whereas' or 'mismatch' are never set aside. The implementation fingerprint changed; use new run IDs. Earlier runs keep their reports.

## Rubric 1.3.0 (opt-in)

Adds two rubric dimensions derived from `priorities.md`: inference design and analysis fit (unit of inference versus lower-level observations, scale and model fit, hand-set thresholds, treatment-batch confounding, exploratory versus confirmatory) and negative and absence evidence (detection sensitivity, positive controls, no claim above moderate on non-detection alone). The review's `reporting_and_statistics` accepts up to ten findings and four new aspects (`unit_of_inference`, `scale_and_model`, `batch_and_metadata`, `negative_evidence`). The page prompt asks for the detection limit of negative observations. The cross-check prompt now says to omit checks whose passages agree and to keep reasoning out of the fields, after cross-check items labelled as conflicts were seen with the explanation 'no conflict found' and with visible self-correction. Otherwise identical to 1.2.0. Select with `"rubric": "scientific-method-v1.3.0"`; use a new run ID. Not yet evaluated across independent studies; see the comparison register.

## Rubric 1.2.0 (opt-in)

Adds a cross-check stage before the review: a text-only call compares passages of the original text for conflicts in thresholds, sample sizes, amounts and durations, tests and software, generalising statements and wording (dimension 10). Quotes are verified by code against the cited block, across neighbouring blocks and page breaks, ignoring bare page numbers and manuscript line numbers at line ends. Results are in `crosscheck.json` and are passed to the review. New settings `crosscheck_num_predict` and `crosscheck_text_chars`. Legend detection also accepts `Fig. 1 | text` and dash styles. Select with `"rubric": "scientific-method-v1.2.0"`; use a new run ID.

## Rubric 1.1.1 (opt-in)

Fixes truncated text fields. When the model opened a quotation inside a text value, constrained JSON decoding ended the string at the quotation mark and the rest of the sentence was lost (first seen with rubric 1.1.0; the same pattern appears in earlier runs). Rubric 1.1.1 is 1.1.0 plus an output rule against double quotation marks in text values. All rubrics now also raise the quality flag `suspected_truncated_text` for values that end mid-sentence (trailing whitespace, trailing punctuation such as an opening bracket, colon, comma or semicolon, or a trailing function word). The flag is advisory, not a failure. Runs made with 1.1.0 keep their results and are affected by the defect. Select with `"rubric": "scientific-method-v1.1.1"`; use a new run ID.

## Rubric 1.1.0 (opt-in)

Select with `"rubric": "scientific-method-v1.1.0"` in manifest settings; the default stays 1.0.0 and its prompts and schemas are unchanged. Adds two rubric dimensions: claim-measurement linkage (what each assay measures versus what the claim is about; link status directly shown, inferred, not shown or unclear) and reporting and statistics (experimental units, replication, error bars, tests, multiplicity, significance wording, software parameters, data availability, consistency between Methods, legends and Results). Page records gain `measurement_target` and `statistics_reported`; the review gains `claim_measurement_links` and `reporting_and_statistics`. Prompts and schemas are selected by rubric version. The implementation fingerprint changed, so earlier run IDs cannot be resumed; use a new run ID. Consider `review_num_predict` of about 14000 because the review output is longer. Eighteen offline tests pass.

## 1.0.3

Bound previously unbounded review-output lists to eight items. This prevents runaway repetition inside fields such as triangulation evidence streams. Existing limits are preserved; the page-analysis format and scientific prompts are unchanged.

Source augmentation can retain completed expanded-context page calls explicitly with `--reuse-added-pages-from`. The full source package and provider must match, and each imported request is verified by the existing exact-input checks. Earlier-context main records remain distinct from those exact expanded-context cache entries. Failed syntheses remain preserved in their original run.

## Source-augmentation helper

Add an explicitly fingerprinted orchestration helper for additional PDF sources. Earlier-context page records retain their original provenance and are distinguished from new page analyses under the expanded source package. A fresh combined synthesis receives both records and original text/methods. Four synthetic regression checks reject changed/removed earlier sources or altered page images; sixteen offline tests pass in total. Scientific prompts and the existing package implementation are unchanged.

## 1.0.2

Cap generated citation lists at eight source IDs per item. This prevents plot-label enumeration from exhausting output tokens, without changing scientific prompts or treating scientific mistakes as operational failures. Structural quality warnings remain separate from scientific evaluation.

Add explicit `--reuse-completed-from` recovery into a new run. Compatible completed page responses retain their original requests, responses, settings, metrics and provenance. Reuse verifies scientific prompts, source image hashes, source IDs, model/options and output structure. Only output ceilings and citation-list ceilings may differ; imported responses are explicitly marked as earlier outputs, not relabeled as newly generated. Failed attempts stay at their original run. Twelve offline tests pass, including integration, altered-context rejection, failed-job exclusion and response-tampering checks.

## 1.0.1

Original page layouts can place figure legends on separate pages, split a legend over several text blocks, and omit a text-readable figure number from the image page. Retain candidate legend continuation blocks up to the next caption heading on that page. When no figure label can be extracted from the target page, supply available legend candidates within the existing caption budget and explicitly mark them as unlinked. This is context retrieval, not perfect figure segmentation or a scientific answer correction.

A synthetic regression test covers separated legends and continuation blocks. Ten offline tests pass. The scientific rubric and model evaluation policy are unchanged. Code changes require a new run ID, preserving earlier protocol records.
