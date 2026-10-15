# Human scientific evaluation

Review central claims against original data presentations, figure legends and relevant methods. Confirm the experiment actually tests the interpretation under scrutiny. Distinguish a missing experiment from a missing supplement, extraction failure, overlooked method or uncertain local context. A claim may be well qualified even if the underlying mechanism remains unresolved.

Where feasible, have two reviewers independently annotate a subset, then adjudicate material disagreements. Preserve original independent annotations separately; feed only adjudicated records to the recurrence aggregator. Review errors and successful assessments across domains. Group companion papers and overlapping datasets under one independence group. Include exploratory papers for development only and exclude them from primary recurrence counts.

Use one JSON object per line in `data/annotations.jsonl`. Every field below is required:

```json
{"paper_id":"study-001","run_id":"cohort-01","claim_id":"C1","family":"causal_overreach","severity":"material","confirmed":true,"origin":"model_reasoning","independence_group":"independent-study-001","notes":"Explain the specific inference error and the human adjudication.","source_reference":"main.p008.b003; main.p015.b002; Figure 5A"}
```

Use a returned major-claim ID, or `study` for an overall omission. The command checks paper/run IDs, claim IDs, cohort independence groups and duplicates. Do not count multiple annotations of the same paper, claim, family and origin as independent evidence. Keep pre-adjudication revisions separately rather than duplicating them in the final file.

Families are defined in `scientific_review/schemas/annotation.json`: causal overreach, necessity/sufficiency confusion, hypothesis as fact, evidence ranking, missed triangulation, false orthogonality, shared dependency, missed validation, false missing validation, design/controls, replication/independence, statistics interpretation, method integration, visual interpretation, other scientific error, and citation format.

Severity is `minor`, `material` or `major`. Origin is `model_reasoning`, `extraction`, `missing_input`, `workflow` or `unclear`. A recurrence candidate requires human confirmation, material/major severity, model-reasoning origin, a scientific family, nonexploratory papers and at least three distinct independence groups by default. Group assignments must match the frozen manifest. Extraction, missing-input and workflow errors remain visible but do not count as scientific reasoning recurrence.

```sh
paper-review evaluate data/annotations.jsonl data/runs/cohort-01 --output data/evaluation.json
```

Do not interpret counts as calibrated accuracy, sensitivity, specificity or error rates. This error log has no denominator of all claim-level opportunities; an unannotated paper is not a confirmed error-free paper. Preserve the number of reviewed papers, reviewed claims, human review coverage, domain mix, exclusions and reviewer agreement in the cohort evaluation. The aggregator reports cohort and annotated-paper counts, but does not infer unrecorded successful assessments.

After the first approximately 20 independent studies, inspect recurrence candidates together with counterexamples and domain context. Make any justified prompt or workflow revision in a new protocol, ideally test it on held-out independent manuscripts, and retain the original results. Do not automatically revise prompts or exclude papers because a single output is disappointing.
