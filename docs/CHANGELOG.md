# Changes

## Source-augmentation helper

Add an explicitly fingerprinted orchestration helper for additional PDF sources. Earlier-context page records retain their original provenance and are distinguished from new page analyses under the expanded source package. A fresh combined synthesis receives both records and original text/methods. Four synthetic regression checks reject changed/removed earlier sources or altered page images; sixteen offline tests pass in total. Scientific prompts and the existing package implementation are unchanged.

## 1.0.2

Cap generated citation lists at eight source IDs per item. This prevents plot-label enumeration from exhausting output tokens, without changing scientific prompts or treating scientific mistakes as operational failures. Structural quality warnings remain separate from scientific evaluation.

Add explicit `--reuse-completed-from` recovery into a new run. Compatible completed page responses retain their original requests, responses, settings, metrics and provenance. Reuse verifies scientific prompts, source image hashes, source IDs, model/options and output structure. Only output ceilings and citation-list ceilings may differ; imported responses are explicitly marked as earlier outputs, not relabeled as newly generated. Failed attempts stay at their original run. Twelve offline tests pass, including integration, altered-context rejection, failed-job exclusion and response-tampering checks.

## 1.0.1

Original page layouts can place figure legends on separate pages, split a legend over several text blocks, and omit a text-readable figure number from the image page. Retain candidate legend continuation blocks up to the next caption heading on that page. When no figure label can be extracted from the target page, supply available legend candidates within the existing caption budget and explicitly mark them as unlinked. This is context retrieval, not perfect figure segmentation or a scientific answer correction.

A synthetic regression test covers separated legends and continuation blocks. Ten offline tests pass. The scientific rubric and model evaluation policy are unchanged. Code changes require a new run ID, preserving earlier protocol records.
