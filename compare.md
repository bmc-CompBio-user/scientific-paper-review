# Expert–pipeline review comparisons

This is a living record of comparisons between expert reviews and pipeline reports. Its purpose is to identify useful assessments, material disagreements, omissions, and eventually repeated reasoning problems across independent studies. Ordinary model mistakes are expected. A single comparison does not justify changing the scientific rubric.

Keep original reviews, model responses, prompts and run artifacts unchanged and local. This document contains comparison summaries; it does not replace source-level adjudication or the structured annotations described in [the evaluation guide](docs/EVALUATION.md).

## How to extend this document

1. Add a case using the template below, with a stable study ID and independence group. Revisions, companion manuscripts and overlapping datasets do not constitute independent replications.
2. Record which expert review, pipeline report and run were compared. Mark unavailable provenance explicitly; do not infer a run or protocol version from a report filename.
3. Separate agreement, disagreement, omission, and internal inconsistency. Distinguish comparison of the reviews from checking either review against the manuscript.
4. Before confirming a scientific error, inspect the original figures, legends, methods and supplied supplements. Check whether the relevant evidence was available to the model and whether extraction or context limitations explain the result. An expert review is a reference assessment, not an infallible answer key.
5. Record successful assessments and counterexamples as well as errors. Update the pattern register only after assessing independence and adjudication status. Do not interpret the number of comments as an accuracy score.
6. Keep manuscript files, private paths and full review text outside Git. Use case IDs in this public document and retain their source mapping locally.

## Case register

Case narratives contain manuscript-specific content and are kept locally in `outputs/comparisons/` (ignored by Git). Only the case ID, a neutral topic label and a status belong in this public table.

| Case | Topic | Comparison date | Status |
| --- | --- | --- | --- |

## Candidate pattern register

Add entries only after assessing independence and adjudication status. Describe patterns generically, without manuscript-specific claims, molecules or datasets. Repeated comments within a single study do not increase the independent-study count; the evaluation workflow defaults to three independent study groups for a recurrence candidate.

| Candidate pattern | Cases | Current evidence status |
| --- | --- | --- |

## Template for the next comparison

Copy this section, replace placeholders and add the case to the register.

### COMP-XXX — Short topic

**Materials and scope**

- Comparison date:
- Expert review identifier/revision:
- Pipeline report identifier and saved run:
- Protocol/package/model identity:
- Supplied main manuscript and supplements; model input coverage:
- Independence group and relationship to earlier cases:
- Source-level checking performed:
- Adjudication status and unresolved limitations:

**Main difference**

Describe the most consequential agreement or disagreement in a short paragraph.

**Major differences**

| Issue | Expert review | Pipeline report | Source evidence and adjudication |
| --- | --- | --- | --- |
| Add issue | Add assessment | Add assessment | Distinguish verified finding, disagreement, omission and uncertain input coverage |

**What the pipeline did well**

Record successful assessments and relevant counterexamples.

**Problems visible within the report**

Record contradictions, duplicated requests or unsupported certainty separately from manuscript-dependent scientific judgments.

**Revision priorities**

Separate reporting improvements, necessary reanalysis, claim qualification and experiments required only if stronger claims are maintained.

**Candidate patterns and follow-up**

Link to earlier independent cases where appropriate. Record source references, reviewer disagreements, confirmation status and any structured annotation IDs. Do not infer a systematic problem from one case.
