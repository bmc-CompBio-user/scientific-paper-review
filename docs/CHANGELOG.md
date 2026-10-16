# Changes

## 1.0.1

Original page layouts can place figure legends on separate pages, split a legend over several text blocks, and omit a text-readable figure number from the image page. Retain candidate legend continuation blocks up to the next caption heading on that page. When no figure label can be extracted from the target page, supply available legend candidates within the existing caption budget and explicitly mark them as unlinked. This is context retrieval, not perfect figure segmentation or a scientific answer correction.

A synthetic regression test covers separated legends and continuation blocks. Ten offline tests pass. The scientific rubric and model evaluation policy are unchanged. Code changes require a new run ID, preserving earlier protocol records.
