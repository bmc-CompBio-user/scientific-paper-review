# Priorities for reviewing life-science experimentation and computation

## Purpose and use

Evaluate whether the experimental design, measurements and analysis support the scientific claims. Prioritise biological relevance, effect magnitude, uncertainty, independent replication and causal validity over statistical significance alone.

Apply these instructions proportionately to exploratory and confirmatory work. Do not demand completion of every proposed mechanism. Distinguish what was directly observed, what is consistent with the data, what is hypothesised and what has been causally established.

This document records review priorities. It does not automatically modify the pipeline's frozen scientific prompts, invalidate earlier runs or establish that a model error is systematic. Protocol changes require explicit versioning and evaluation across independent studies.

## 1. Hypotheses, claims and the statistical question

- Identify the exact hypothesis and its wording, including outcome, comparison, predicted direction or relationship and biological scope.
- Determine whether it was formulated before examining the relevant results. If timing is undocumented, label it unclear rather than assuming prespecification.
- Distinguish exploratory, data-generated hypotheses from confirmatory tests. Exploration is legitimate; presenting it as prospective confirmation is not.
- Check whether the statistical model, interaction term or contrast actually tests the stated hypothesis. A significant result in one group and a nonsignificant result in another does not establish a difference between groups.
- Assess whether the endpoint is biologically meaningful and whether the conclusions extend beyond the measured system, outcome or time window.

## 2. Independent replication and the unit of inference

- Identify the experimental unit: the independently sampled or assigned unit relevant to the claim. Distinguish it from lower-level observations and technical measurements.
- Require explicit counts of biological replicates and technical repeats. Cells, image fields, wells, reads, genes and repeated measurements do not automatically constitute independent biological N.
- Distinguish within-sample variability from between-replicate variability. Large numbers of observations within one sample cannot replace independent replication.
- In scRNA-seq, thousands of cells from one donor per condition still provide one donor per condition for a donor-level condition comparison. Cell-level testing cannot separate condition from donor in that design.
- Where replication exists, use donor/sample-level aggregation or an appropriate hierarchical model. Preserve pairing, nesting and repeated-measure dependence. Pseudobulk does not rescue N=1.
- With N=1 per condition, retain descriptive and exploratory observations, but do not treat within-sample p-values or narrow cell-level intervals as evidence of a reproducible population-level effect.

## 3. Sampling, representativeness and generalisation

- Define the target population and how samples were obtained. Evaluate selection, inclusion criteria and relevant biological diversity.
- Keep representativeness distinct from replication: repeated experiments in one cell line may establish repeatability within that system without establishing generality across cell types, donors or organisms.
- Consider relevant restrictions such as sex, age, genotype, disease state, culture conditions and laboratory setting.
- Match the scope of conclusions to the sampled population and experimental context. State which extensions remain hypotheses.

## 4. Power, precision and strength of evidence

- Exploratory studies often lack an a priori power calculation. Its absence alone is not automatically a major flaw or proof of inadequate power.
- Evaluate independent N, variability, effect estimates and uncertainty. Limited precision weakens the conclusions that can be drawn from statistical assessment, even when a p-value crosses a threshold.
- Small, noisy studies can yield unstable or exaggerated effect estimates. Treat these as uncertain rather than automatically strong evidence.
- Nonsignificance is not evidence of no effect. Ask whether intervals exclude biologically meaningful effects; equivalence claims need an appropriate margin and analysis.
- For confirmatory work, assess sample-size justification against the primary question and a meaningful target effect. Do not substitute retrospective observed power calculated from the observed effect for uncertainty assessment.

## 5. Effect sizes and inferential uncertainty

- Prioritise effect magnitude, biological relevance and uncertainty together. A large uncertain estimate is not automatically compelling; a tiny precisely estimated effect is not automatically important.
- Report effect estimates with confidence intervals, preferably 95%, for the actual comparison of interest. For paired designs, show uncertainty in the paired contrast rather than relying only on separate group means.
- Inferential claims require inferential uncertainty. SEM is acceptable when explicitly labelled; confidence intervals are generally more interpretable. SD describes dispersion and can be useful, but does not substitute for uncertainty in an estimated effect.
- Show independent biological observations where practical. Define error bars, interval level, calculation method and the unit used to calculate them.
- Account for clustering, pairing, repeated measurements and fitted-model uncertainty. Technical replication must not create deceptively precise biological inference.
- Do not infer significance mechanically from overlap or non-overlap of separate group error bars.

## 6. Measurement scale, transformations and model assumptions

- Flag t-tests or ANOVA on raw ratios or percentages when their assumptions are unsupported, particularly with small independent N. The scale alone does not prove that an analysis is invalid.
- For positive fold changes and multiplicative ratios, ordinarily use log-scale visualisation so reciprocal changes are symmetric. Consider analysis on the log scale when scientifically and statistically appropriate; report back-transformed effects and intervals.
- Distinguish count-derived proportions from continuous fractional measurements. For count-derived percentages, retain numerator and denominator and consider binomial/logit models, accounting for overdispersion and biological clustering as needed. Logit transformation followed by a t-test is not an automatic solution.
- Preserve numerator/denominator information, pairing and dependencies created by shared controls. A noisy or near-zero denominator can make ratios unstable.
- Explain handling of zeros, ones and detection limits. Do not add arbitrary pseudocounts solely to enable logarithms.
- Distinguish percentage-point differences, relative percentage changes, fold changes and odds ratios.
- A logarithmic plotting axis does not transform the statistical analysis. Neither transformation nor a nonparametric test repairs pseudoreplication, confounding or poor sampling.
- Evaluate relevant residual/error assumptions and model adequacy. A nonsignificant normality test with tiny N does not establish those assumptions.

## 7. Time courses and repeated measurements

- Determine whether successive measurements come from the same unit or from independent destructive samples. Identify the biological question: trajectory, rate, onset, peak, duration or a prespecified time-point contrast.
- Do not use ordinary two-way ANOVA when it ignores repeated-measure correlation or other dependence. Repeated-measures ANOVA can be appropriate under its assumptions; mixed-effects, longitudinal or kinetic models may better match the design and hypothesis.
- Assess the treatment-by-time question where relevant. Avoid a series of uncoordinated time-point tests that ignores multiplicity or temporal structure.
- Document missing time points and assess whether their absence could depend on treatment or outcome.

## 8. Controls, measurement validity and causal inference

- Evaluate controls by the alternative explanations they address. Positive controls establish assay competence; negative, vehicle, mock, specificity and procedural controls serve different purposes. Require relevant controls or a justified alternative rather than a fixed control count.
- Check assay specificity, calibration, dynamic range, saturation, background, normalisation and whether the measurement is a proxy for the claimed entity.
- Check dose, total input, exposure time, delivery procedure and other treatment differences that could confound the comparison.
- Separate association, necessity and sufficiency. Artificial delivery, overexpression or high-dose perturbation may establish potential without demonstrating endogenous physiological action.
- Ask whether different experiments actually measure or connect the same molecular species or process. Compatible observations do not by themselves establish an intervening molecular link.
- Assess rescue, independent perturbations and orthogonal validation by their shared assumptions and failure modes. Multiple readouts of one intervention are not automatically independent confirmation.
- Check that proposed experiments predict the correct direction of intervention and discriminate between competing explanations.

## 9. Bias, batches and metadata

- Assess allocation and measurement procedures for plausible systematic bias. Consider randomisation or balanced processing where feasible.
- Blinding may be difficult or impractical in basic research. Evaluate feasibility at individual stages, particularly scoring and analysis. Its absence alone is not automatically a major flaw; identify a concrete route to bias before assigning substantial concern.
- Document relevant batch structure in sample-level metadata: preparation date, experimental run, donor, reagent lot, operator, plate, instrument and sequencing run, as applicable.
- Check whether treatment is confounded with batch. Complete treatment–batch confounding cannot be resolved by statistical adjustment.
- Do not automatically remove batch effects. Justify adjustment against the design, preserve biological signal and report the procedure and its consequences.

## 10. Multiplicity, exclusions and analytical flexibility

- Identify the family of hypotheses tested and the number of outcomes, genes, contrasts, thresholds and analysis variants explored. Use appropriate error control for the intended claims.
- Dependence among measurements or a supposedly conservative individual test does not by itself remove the multiple-testing problem.
- Report selection of endpoints, gene sets, examples and models. Distinguish prespecified decisions from choices made after observing results.
- Document exclusions, failed experiments, missing observations and outlier handling, with counts and reasons by group. Consider sensitivity to reasonable alternative choices.
- Check consistency of thresholds, methods and reported results across the manuscript and supplements.

## 11. Figure legends, N and complete data presentation

- Every experimental figure legend must state N and define what it counts, separately for each panel or group when these differ.
- Distinguish independent biological replicates from technical repeats and lower-level observations. State which unit underlies statistical tests and error bars; identify the test, error measure and relevant normalisation.
- For an example image or blot, state how many independent experiments were performed, how the displayed example was selected and where the remaining results can be inspected. If N=1, state it explicitly.
- The word “representative” does not establish representativeness. Require quantitative evidence across independent experiments and access to all underlying data supporting the claim, through supplements or an appropriate repository. A selected example cannot substitute for the full evidence.
- Provide original images/blots and quantitative source data with sufficient annotation to connect observations to samples, conditions and figures. Protect sensitive information through an appropriate access route.
- Never infer N solely from plotted points. Missing or ambiguous N limits assessment; flag missing reporting without assuming replication was absent.

## 12. Computational reproducibility and high-throughput data

- Report software versions and relevant parameters, including deviations from defaults, reference genome/annotation and database releases, preprocessing, filtering, normalisation and model settings.
- Provide executable analysis code or workflows, dependencies/environments and relevant random seeds. Make the route from raw data to figures reconstructable.
- For high-throughput experiments, deposit raw data and essential metadata in appropriate repositories; supply processed data, sample mappings and accession identifiers. Provide reviewer access when needed for assessment. Use documented controlled access where ethical or legal restrictions prevent open release.
- For sequencing, report design-relevant details such as strandedness, read assignment, multimapping, quality criteria and genomic intervals. Explain custom analyses precisely.
- For predictive computation, keep preprocessing, feature selection and tuning within training folds. Prevent donor-, sample- or study-level leakage; preserve an independent final test set and use comparable benchmarking protocols.
- Assess robustness to reasonable analysis choices and relevant independent validation. Computational reproducibility alone does not establish biological or causal validity.

## 13. Required review output and proportionate recommendations

For each material concern, state:

1. What the manuscript actually reports, with figure, page or method references.
2. What can be inferred and which claim is affected.
3. What remains uncertain, including whether information may be missing from the supplied material or extraction.
4. The consequence for evidence strength and generalisation.
5. A proportionate remedy: reporting clarification, reanalysis, narrowed claim or an additional discriminating experiment.

Distinguish an unreported method from an absent method. Do not prescribe new experiments when appropriate qualification or reanalysis would resolve the claim. If a stronger mechanism is maintained, identify the specific additional evidence it requires. Record strengths and successful validation as well as limitations.

## Supporting references

These sources support relevant principles; they do not make every recommendation a universal requirement across all life-science designs.

- [ARRIVE 2.0](https://arriveguidelines.org/arrive-guidelines): experimental units, sample size, controls and transparent reporting in animal research.
- [ASA statement on p-values](https://doi.org/10.1080/00031305.2016.1154108): effect magnitude, context and limits of significance thresholds.
- [Cumming, Fidler and Vaux: Error bars in experimental biology](https://pmc.ncbi.nlm.nih.gov/articles/PMC2064100/): descriptive versus inferential error bars and independent replication.
- [GraphPad: Ratios and fold-change visualisation](https://www.graphpad.com/support/faq/graphing-data-expressed-as-fold-changes-or-ratios/): reciprocal symmetry on a logarithmic scale.
- [GraphPad: Paired versus ratio t-tests](https://www.graphpad.com/guides/prism/latest/statistics/stat_paired_or_ratio_t_test.htm): additive versus multiplicative comparisons.
- [R documentation: Generalised linear models](https://search.r-project.org/R/refmans/stats/help/glm.html): count-derived proportions and binomial denominators.
- [GraphPad: Repeated-measures experimental design](https://www.graphpad.com/guides/prism/latest/statistics/stat_experimental_design_tab_2way.htm): matching the analysis to dependence in the design.
- [Nature reporting standards](https://www.nature.com/nature/editorial-policies/reporting-standards): data, code, materials and access documentation.
