"""Compact text rendering of an experiment knowledge graph (SEKG experiments.json and unresolved_issues.json) for the review prompts."""
import hashlib
import json
from pathlib import Path
from .common import digest

FIELD_GROUPS = (
    ('system', ('organism', 'tissue', 'cell_type', 'cell_line', 'biological_source', 'system_class')),
    ('conditions', ('comparison', 'intervention', 'treatment', 'perturbation', 'exposure', 'experimental_groups', 'comparator_groups', 'controls')),
    ('measurement', ('readout', 'method', 'target', 'unit', 'data_modality')),
    ('design', ('experimental_unit', 'biological_replicates', 'technical_replicates', 'batches', 'blocked_conditions', 'time_points', 'sample_preparation')),
    ('analysis', ('data_source', 'computational_method', 'statistical_method', 'normalization', 'derived_measurements')),
)
MARK = {'ambiguous': ' [ambiguous]', 'inferred': ' [inferred]'}
KEY_FIELDS = {'conditions.controls', 'design.experimental_unit', 'design.biological_replicates', 'design.technical_replicates', 'analysis.statistical_method', 'analysis.normalization'}


def kg_files(directory):
    directory = Path(directory)
    return directory/'experiments.json', directory/'unresolved_issues.json'


def kg_digest(directory):
    """Hash of the graph files, recorded with the paper so a changed graph needs a new run ID."""
    experiments_path, issues_path = kg_files(directory)
    if not experiments_path.exists():
        raise ValueError('Knowledge graph not found: ' + str(experiments_path))
    return hashlib.sha256('|'.join(digest(p) if p.exists() else '-' for p in (experiments_path, issues_path)).encode()).hexdigest()


def text(value):
    if isinstance(value, list):
        return '; '.join(text(v) for v in value)
    return ' '.join(str(value).split())


def fields(record, group, names):
    reported, missing = [], []
    section = record.get(group) or {}
    for name in names:
        field = section.get(name)
        if not isinstance(field, dict) or field.get('status') in (None, 'not_reported', 'not_applicable') or field.get('value') in (None, [], ''):
            missing.append(name)
            continue
        reported.append(f"{name}={text(field['value'])}{MARK.get(field['status'], '')}")
    return reported, missing


def render_record(record):
    panels = ', '.join(f"{p.get('figure', '')}{p.get('panel') or ''}".strip() for p in record.get('panels') or []) or 'no panel'
    lines = [f"{record['id']} [{record.get('kind', '')}] {record.get('name', '')} | panels: {panels}"]
    absent = []
    for group, names in FIELD_GROUPS:
        reported, missing = fields(record, group, names)
        if reported:
            lines.append(f'  {group}: ' + '; '.join(reported))
        absent += [f'{group}.{n}' for n in missing]
    links = []
    if record.get('consumes'):
        links.append('consumes ' + ', '.join(c.get('target', str(c)) if isinstance(c, dict) else str(c) for c in record['consumes']))
    if record.get('derived_from'):
        links.append('derived from ' + ', '.join(c.get('target', str(c)) if isinstance(c, dict) else str(c) for c in record['derived_from']))
    if links:
        lines.append('  links: ' + '; '.join(links))
    absent = [a for a in absent if a in KEY_FIELDS]
    if absent:
        lines.append('  not reported by the extraction: ' + ', '.join(absent))
    if record.get('notes'):
        lines.append('  notes: ' + text(record['notes'])[:400])
    return '\n'.join(lines)


def render_dataset(dataset):
    parts = [f"{dataset['id']} {dataset.get('name', '')} | origin: {dataset.get('origin', '')}"]
    produced = dataset.get('produced_by')
    if produced:
        parts.append('produced by ' + (produced.get('target', '') if isinstance(produced, dict) else str(produced)))
    if dataset.get('derived_from'):
        parts.append('derived from ' + ', '.join(d.get('target', str(d)) if isinstance(d, dict) else str(d) for d in dataset['derived_from']))
    accession = dataset.get('accession') or {}
    if accession.get('value'):
        parts.append('accession ' + text(accession['value']))
    if dataset.get('resource'):
        parts.append('resource ' + text(dataset['resource']))
    return ' | '.join(parts)


def render_kg(directory, max_chars):
    """Experiments first, then datasets, then analyses and the extraction's own flags; trimmed to max_chars by dropping flags, analyses and datasets first and experiments last (at least one experiment is kept)."""
    experiments_path, issues_path = kg_files(directory)
    kg = json.loads(experiments_path.read_text())
    issues = json.loads(issues_path.read_text()) if issues_path.exists() else {}
    header = ('EXPERIMENT KNOWLEDGE GRAPH (independent extraction from this manuscript; descriptive, may contain errors; '
              'quotes behind each field were checked by the extraction tool but are not repeated here)')
    sections = [('EXPERIMENTS (they produce data)', [render_record(r) for r in kg.get('experiments', [])]),
                ('DATASETS AND LINEAGE', [render_dataset(d) for d in kg.get('datasets', [])]),
                ('ANALYSES (computations on existing data)', [render_record(r) for r in kg.get('analyses', [])]),
                ('EXTRACTION FLAGS', [f"{kind}: {text(item.get('question') or item.get('message') or item.get('issue') or item.get('description') or item)[:300]}"
                                       for kind in ('issues', 'ambiguities') for item in (issues.get(kind) or [])[:20]] +
                                      [f"discrepancy: {text(d)[:300]}" for d in kg.get('discrepancies', [])[:10]])]
    def build(limits):
        out = [header]
        for (title, items), limit in zip(sections, limits):
            if items:
                out += ['', title] + items[:limit]
        return '\n'.join(out)
    limits = [len(items) for _, items in sections]
    omitted = []
    result = build(limits)
    for index in (3, 2, 1):  # shed flags, then analyses, then datasets, one item at a time from the end
        while len(result) > max_chars and limits[index] > 0:
            limits[index] -= 1
            result = build(limits)
    if len(result) > max_chars:
        while len(result) > max_chars and limits[0] > 1:
            limits[0] -= 1
            result = build(limits)
    dropped = [f'{title}: {len(items) - limit} of {len(items)} omitted' for (title, items), limit in zip(sections, limits) if limit < len(items)]
    if dropped:
        result += '\n\n(trimmed to the character budget; ' + '; '.join(dropped) + ')'
    return result
