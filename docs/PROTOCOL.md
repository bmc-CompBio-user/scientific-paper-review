# Frozen study-neutral protocol v1.0.0

The first objective is to characterize scientific reasoning across approximately 20 independent studies, followed by several dozen if useful. Do not tune prompts to repair each mistake in a development paper. Retain errors and uncertainties, then examine recurrence across studies.

## Review dimensions

- Experimental design, measurement validity, controls, experimental unit, independence, biological versus technical replication, appropriate statistics, uncertainty and confounding.
- Association versus intervention, intervention specificity, causal scope, necessity, sufficiency, rescue, mediation and alternative mechanisms.
- Author-reported findings versus interpretation, explicit hypotheses, reviewer alternatives and discriminating predictions.
- Claim-level evidence rank with a rationale: not assessable, very weak, weak, moderate, strong or very strong. These are reasoned categories, not calibrated probabilities.
- Triangulation across evidence streams, with explicit shared data, samples, reagents and assumptions.
- Orthogonal validation by different measurement principles; different names or panels alone do not establish independence.
- Missing validation ranked by consequence for the central claim, with experiments, competing predictions, and how the interpretation would change.

Read the actual versioned rubric and stage prompts under `scientific_review/prompts/`. These, schemas, Python source and settings are included in the implementation fingerprint. Existing run IDs reject protocol drift. Append-only cohort membership permits additional studies without changing previous entries. A new protocol means a new run ID, and should be analyzed as a separate cohort or paired comparison.

## Evidence and context

Every PDF is hashed. All pages and text blocks are preserved with coordinates, physical page numbers and available printed labels. Full-page images and uniform overlapping tiles are rendered. Figure mentions and captions use conservative text matches; a candidate can refer to another figure or collide between main and supplementary documents. Candidate links require verification. Figures are not promised to be perfectly segmented.

Page-level calls include the current images and text, candidate related legends, selected methods text and an inventory of all supplied pages. Original method pages are selected from explicit hints or heading cues; additional method-like blocks are heuristically collected. This is a retrieval aid, not a guarantee of exhaustive relevant-method selection. Complete extraction remains available for human inspection. Selection omissions are recorded in prompts. Metadata/reference pages are allowed to produce no substantive observations.

The synthesis receives all provisional page records, a whole-document inventory, original methods context, and additional original text within a stated character budget. It is text-only: model-derived evidence records may carry interpretation errors from the image stage. An inventory reference is not equivalent to inspecting its source content. A valid source ID establishes traceability, not entailment. Underlying experimental raw data are not automatically available or reanalyzed.

Mandatory page records and methods context exceeding the configured synthesis budget cause an explicit operational error instead of silent record loss. Optional original-text omissions are listed. Character budgets are conservative controls, not exact token counts; image embeddings and tokenizer behavior affect the true context requirement. Inspect provider token metrics and coverage before trusting long manuscripts. Increase context and budgets in a new protocol when necessary.

## Quality control without paper-specific overfitting

Transport, truncation, JSON parsing and structural schema failures are operational failures. They preserve the attempted response and block that stage until an explicit retry. Resume never silently replaces an attempt. Cached input fingerprints are checked before reuse. A paper failure does not discard other papers.

Unknown/empty citations and inconsistent claim links are quality flags, not automatic paper failure. Scientific mistakes are assessed by humans against the original pages, legends and methods. The primary endpoint is recurring material reasoning errors across independent studies, including false criticism and missed validation. Correct reasoning and justified restraint should also be recorded by evaluators.

Temperature zero and a fixed seed do not establish scientific reliability or exact determinism. Record human review, model identity, protocol identity and input package when comparing runs. The production v1 rubric contains no named-paper answer key.

## Protocol v1.1.0

An opt-in rubric (`scientific-method-v1.1.0`) adds claim-measurement linkage and reporting-and-statistics review. It is a separate protocol: analyze its runs as a different cohort or as a paired comparison with v1.0.0, and keep v1.0.0 results. It was motivated by a first expert comparison (see `compare.md`); the added items are generic and contain no study-specific answers.


## Protocols v1.2.0 and v1.3.0

`scientific-method-v1.2.0` adds a cross-passage consistency check (a text-only stage whose quotes are verified by code). `scientific-method-v1.3.0` adds inference design and analysis fit, and negative and absence evidence, derived from `priorities.md`. Both are opt-in, separate protocols. They were motivated by expert comparisons across six manuscripts that are kept in a private register; the added items are generic and contain no study-specific answers. Because the same manuscripts motivated the change, they cannot also serve as its evaluation: judge v1.3.0 on manuscripts that were not used to write it, and count a finding only when it recurs across independent studies.
