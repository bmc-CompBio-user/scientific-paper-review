"""Human-confirmed, study-independent error recurrence; no automated truth scoring."""
from collections import defaultdict
from pathlib import Path
import json
import jsonschema
from .common import PACKAGE, read, write


def evaluate(annotation_path, run_root, output, minimum_studies=3):
    if minimum_studies < 2:
        raise ValueError('Recurrence requires at least two independent study groups')
    cohort = read(Path(run_root)/'cohort.json')
    schema = read(PACKAGE/'schemas/annotation.json')
    records, groups, seen = [], defaultdict(set), set()
    for number, line in enumerate(Path(annotation_path).read_text().splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        jsonschema.validate(item, schema)
        pid = item['paper_id']
        if pid not in cohort or item['run_id'] != Path(run_root).name:
            raise ValueError(f'Annotation line {number}: unknown paper/run')
        expected_group = cohort[pid].get('independence_group', pid)
        if item['independence_group'] != expected_group:
            raise ValueError(f'Annotation line {number}: independence group differs from frozen cohort')
        key = (pid, item['claim_id'], item['family'], item['origin'])
        if key in seen:
            raise ValueError(f'Duplicate annotation at line {number}')
        seen.add(key)
        review_path = Path(run_root)/'papers'/pid/'review.json'
        if not review_path.exists():
            raise ValueError(f'Annotation line {number}: no completed study review')
        review = read(review_path)
        valid_claims = {c['id'] for c in review['major_claims']}
        if item['claim_id'] != 'study' and item['claim_id'] not in valid_claims:
            raise ValueError(f'Annotation line {number}: unknown claim ID')
        eligible = (item['confirmed'] and item['severity'] in {'material', 'major'}
            and item['origin'] == 'model_reasoning' and item['family'] != 'citation_format'
            and not cohort[pid].get('exploratory', False))
        records.append({**item, 'eligible_for_recurrence': eligible})
        if eligible:
            groups[item['family']].add(expected_group)
    result = {'annotation_count': len(records), 'minimum_independent_groups': minimum_studies,
        'interpretation': 'Human-confirmed recurrence candidates, not proof of systematic error. Different papers from the same study count once. Human adjudication required before changing a frozen protocol.',
        'families': [{'family': family, 'independent_groups': sorted(values), 'count': len(values),
                      'recurrence_candidate': len(values) >= minimum_studies} for family, values in sorted(groups.items())],
        'annotations': records,
        'denominators': {'cohort_papers': len(cohort), 'nonexploratory_papers': sum(not p.get('exploratory', False) for p in cohort.values()),
                         'annotated_papers': len({r['paper_id'] for r in records})}}
    write(output, result)
    return result
