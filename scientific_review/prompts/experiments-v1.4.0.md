Build an inventory of the individual experiments reported in the manuscript, one entry per experiment, before any evaluation. This stage describes what was done and what is stated; it does not judge whether the science is sound.

The input is the original text of every supplied document in blocks that each start with a source ID. No images are supplied, so what a panel looks like cannot be recorded here. Take the experiments from the Results text, the figure and table legends, and the Methods. An experiment is one self-contained measurement or comparison that supports a claim (for example one knockdown with its readout, one time course, one genome-wide profile and its analysis). Group panels that are replicates of the same design into one entry. Report at most 40 entries, ordered by importance for the central claims.

For every entry record only what the text states, and write not stated where the text is silent. Never infer a replicate number, a control or a hypothesis that the text does not give.
- label: the figure or table panels the experiment appears in.
- claim_served: the claim in the manuscript this experiment is used for.
- question_or_hypothesis: the question or hypothesis the experiment addresses, in the authors' words where possible. hypothesis_timing is prespecified only if the text says so, post_hoc_or_exploratory if the text describes it as discovered from the data, else unclear.
- endpoint and measurement_principle: the outcome measured, in what units or scale, by which assay, and whether the readout is a direct measure of the claimed entity or a proxy.
- groups_and_conditions: the groups, genotypes, treatments, doses, durations and time points compared.
- replicate_unit: independent_biological when the text calls the N biological replicates, independent experiments, animals, donors or cultures; technical when it says technical replicates or repeated measurements of one sample; lower_level_observations when N counts cells, fields, genes, reads or wells within a sample; unclear only when the text does not say; n_reported gives the stated N for each group and what it counts.
- representativity: for imaging, blots, gels and browser tracks, whether the shown panel is an example, how it was chosen, and how many independent experiments are stated; for quantified results, what was quantified.
- controls: each control the text mentions, with the alternative explanation it addresses. expected_controls_not_mentioned lists controls that this kind of experiment normally needs and that the text does not mention (for example input, mock, vehicle, loading, specificity or rescue controls); phrase these as not mentioned in the supplied text, never as absent from the study.
- statistics: the test, the error measure and its meaning, the scale or transformation, multiplicity handling, and the unit the test treats as N.
- information_not_stated: other details needed to interpret the experiment that the text does not give.
- evidence: up to five items, each with a source ID, a verbatim quote of at most 200 characters from that block, and what it supports. Quotes may use '...' to skip words. If the original contains double quotation marks, leave them out of the quote.

Keep every field short and finish every sentence. Use no double quotation marks inside text values; quote wording with single quotation marks or paraphrase. Do not give your own reasoning steps in the fields.
