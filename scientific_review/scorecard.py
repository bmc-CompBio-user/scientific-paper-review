"""Executive summary with 0 to 5 scores per dimension.

The scores are indicators computed from the structured findings, not judgements of the biology.
Design, statistics and reporting use the share of checked experiments with a concern per aspect and the review-level reporting statuses; evidence strength is model-judged from the claim analysis."""
import json
from collections import Counter as collections_counter
from .aggregate import recurring_issues, representative

DIMENSIONS = {
    'experimental design': ('replicate_independence', 'unit_of_inference', 'batch_and_confounding', 'time_course_design'),
    'statistical procedures': ('scale_and_model', 'reference_normalization', 'multiplicity_and_thresholds', 'negative_evidence', 'statistical_tests', 'multiple_testing'),
    'reporting': ('representativity', 'uncertainty_display', 'error_representation', 'experimental_units', 'replication', 'software_and_parameters', 'data_availability',
                  'significance_wording', 'batch_and_metadata', 'internal_consistency'),
}
STATUS_PENALTY = {'adequate': 0.0, 'partly_reported': 0.4, 'unclear': 0.6, 'not_found_in_reviewed_material': 0.8, 'inconsistent': 1.0}
LINK_POINTS = {'directly_shown': 1.0, 'inferred': 0.6, 'unclear': 0.4, 'not_shown': 0.1}
RATING_POINTS = {'very_strong': 1.0, 'strong': 0.85, 'moderate': 0.6, 'weak': 0.3, 'very_weak': 0.1, 'not_assessable': 0.5}
LABEL = {5: 'few concerns', 4: 'some concerns', 3: 'several concerns', 2: 'many concerns', 1: 'extensive concerns', 0: 'extensive concerns'}


def half(score):
    return max(0.0, min(5.0, round(score * 2) / 2))


def aspect_penalties(checks, review):
    n = max(1, len(checks))
    concerned = {}
    for result in checks:
        seen = set()
        for item in result['items']:
            if item['status'] == 'concern' and (item.get('figure_check') or {}).get('answer') != 'visible':
                seen.add(item['item'])
        for aspect in seen:
            concerned[aspect] = concerned.get(aspect, 0) + 1
    review_level = {f['aspect']: STATUS_PENALTY.get(f['status'], 0.5) for f in review.get('reporting_and_statistics', [])}
    penalties = {}
    for aspect in {a for names in DIMENSIONS.values() for a in names}:
        signals = []
        if aspect in concerned:
            signals.append(min(1.0, concerned[aspect] / n))
        if aspect in review_level:
            signals.append(review_level[aspect])
        penalties[aspect] = {'experiments_with_concern': concerned.get(aspect, 0), 'experiments_checked': len(checks), 'review_level': review_level.get(aspect),
                             'penalty': sum(signals) / len(signals) if signals else 0.0}
    return penalties


def evidence_score(review):
    claims = review.get('major_claims', [])
    if not claims:
        return None, 'no claims analysed'
    links = {x['claim_id']: x['link_status'] for x in review.get('claim_measurement_links', [])}
    essential = {}
    for gap in review.get('validation_gaps', []):
        if gap.get('priority') == 'essential_for_claim':
            essential[gap['claim_id']] = essential.get(gap['claim_id'], 0) + 1
    points = []
    for claim in claims:
        base = LINK_POINTS[links[claim['id']]] if claim['id'] in links else RATING_POINTS.get(claim['evidence_strength'], 0.5)
        points.append(max(0.0, base - 0.15 * essential.get(claim['id'], 0)))
    return half(5 * sum(points) / len(points)), f"{len(claims)} major claims; link to the measured entity where analysed (directly shown, inferred, not shown), else the model's claim rating; minus 0.15 per essential validation gap"


def scores(checks, review):
    penalties = aspect_penalties(checks, review)
    out = {}
    for dimension, names in DIMENSIONS.items():
        parts = [(a, penalties[a]) for a in names]
        mean = sum(p['penalty'] for _, p in parts) / len(parts)
        worst = sorted(parts, key=lambda ap: -ap[1]['penalty'])[:3]
        out[dimension] = {'score': half(5 * (1 - mean)), 'drivers': [(a, p) for a, p in worst if p['penalty'] > 0]}
    score, basis = evidence_score(review)
    claims = review.get('major_claims', [])
    links = collections_counter([x['link_status'] for x in review.get('claim_measurement_links', [])])
    essential = sum(1 for g in review.get('validation_gaps', []) if g.get('priority') == 'essential_for_claim')
    ratings = collections_counter([c['evidence_strength'] for c in claims])
    if score is not None:
        basis = (f"{len(claims)} major claims; model ratings " + ', '.join(f'{n} {k.replace("_", " ")}' for k, n in sorted(ratings.items(), key=lambda kv: -kv[1])) +
                 (f"; link to the measured entity: " + ', '.join(f'{n} {k.replace("_", " ")}' for k, n in links.items()) if links else '') + f"; {essential} essential validation gaps")
    out['evidence strength'] = {'score': score, 'basis': basis, 'drivers': []}
    return out


def describe(aspect, p):
    bits = []
    if p['experiments_checked'] and p['experiments_with_concern']:
        bits.append(f"{p['experiments_with_concern']} of {p['experiments_checked']} experiments")
    if p['review_level'] is not None:
        bits.append('review-level: ' + {v: k for k, v in STATUS_PENALTY.items()}.get(p['review_level'], 'noted').replace('_', ' '))
    return f"{aspect.replace('_', ' ')} ({'; '.join(bits)})"


def executive_summary(code, title, source, checks, review, coverage):
    result = scores(checks, review)
    groups, _ = recurring_issues(checks)
    lines = [f'# Executive summary: {code}', '', f'**{title}**', '', source, '',
             'Scores are indicators from the structured findings of this review (0 to 5 in half steps; 5 means few concerns about the formal aspect). They are not a judgement of the biology and not a recommendation about the paper. '
             'They rest on the supplied main text only: ' + coverage, '',
             '| Dimension | Score | What drives it |', '|---|---|---|']
    for dimension in ('evidence strength', 'experimental design', 'statistical procedures', 'reporting'):
        r = result[dimension]
        if r['score'] is None:
            lines.append(f'| {dimension} | n/a | {r["basis"]} |')
            continue
        drivers = r['basis'] if dimension == 'evidence strength' else '; '.join(describe(a, p) for a, p in r['drivers']) or 'no concern raised'
        lines.append(f'| {dimension} | {r["score"]:g} / 5 | {drivers} |')
    lines += ['', '## Central claims as stated by the authors', '', '(extracted by the review model from the text; the first three of the major claims)', '']
    lines += [f"- {c['authors_claim']}" for c in review.get('major_claims', [])[:3]]
    lines += ['']
    lines += ['## Main formal issues, recurring across experiments', '']
    for g in groups[:5]:
        lines.append(f"- {g['theme']}: {len(g['items'])} concerns in {len(g['labels'])} experiments ({', '.join(g['aspects'])}). Example ({representative(g)['label']}): {representative(g)['finding'][:260]}")
    if not groups:
        lines.append('- none grouped')
    statuses = [f['status'] for f in review.get('reporting_and_statistics', [])]
    sparse = bool(statuses) and sum(s == 'not_found_in_reviewed_material' for s in statuses) / len(statuses) >= 0.6
    lines += ['', '## Notes', '',
              '- Evidence strength is the least validated score: it comes from the review model\'s claim analysis, not from checked findings.',
              '- Absence findings mean not stated in the supplied text; supplements, source data and the content of figure panels were not searched.',
              *(['- Most review-level reporting statuses are not found in the supplied text, which pulls the statistics and reporting scores down; supplementary files may hold the missing information.'] if sparse else []),
              '- Design, statistics and reporting are computed from the share of checked experiments with a concern per aspect and from the review-level reporting statuses; the full list is in the report.', '']
    return '\n'.join(lines), result
