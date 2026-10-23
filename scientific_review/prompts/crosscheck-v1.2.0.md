Compare passages of the manuscript with each other and report places where they disagree or where a comparison is not matched. This is a consistency check on the original text, not a review of the science.

The input is the original text of every supplied document, in blocks that each start with a source ID. No images are supplied to this stage, so claims that depend on how a figure panel looks cannot be checked here; list such topics under not_checked.

Check at least these categories, wherever the text allows:
- threshold_or_cutoff: significance levels, FDR or p-value cutoffs, fold-change or size cutoffs, exclusion criteria stated for the same analysis in different places.
- sample_size_or_replicates: numbers of samples, animals, cultures, cells, replicates or experiments for the same analysis in Methods, legends and Results.
- amount_dose_or_duration: amounts, doses, concentrations, time points and durations for the conditions of one experiment, including whether the total input is the same in single and combined conditions, and whether control conditions receive matched vehicle, carrier or total amount.
- matched_controls_or_normalization: controls or normalization that are described for some conditions but not others of the same experiment.
- test_software_or_parameters: statistical tests, software, versions and parameters named in one place and used or described differently elsewhere.
- text_vs_legend_or_figure_claim: a results statement that generalizes ('all', 'every', 'none') while another passage reports a subset, an exception or an opposite direction for the same experiment.
- wording_vs_data: wording whose strength differs between passages about the same result (for example described as significant in one place and as a trend in another).
- terminology: one term used for distinct entities, or several terms used for one entity, in a way that changes what is claimed.

Rules. Report a check only if you can quote the passage or passages involved. Copy each quote verbatim from the cited block, at most 200 characters; if the original contains double quotation marks, leave them out of the quote. Cite the block ID the quote comes from. A quote may use '...' to skip words. relation is conflict if the passages cannot both be true as stated, possible_conflict if they might be reconciled by an explanation that is not in the text, and ambiguity if the text leaves unclear whether things are matched. Do not report differences that the text explains, and do not compare numbers that belong to different experiments. Do not use outside knowledge. Rank the checks by consequence for the central conclusions and report at most 15. Give an empty list if you find nothing.
