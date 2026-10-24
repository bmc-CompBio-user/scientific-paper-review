import json
import platform
import re
import sys
from pathlib import Path
import jsonschema
import pymupdf
from . import __version__
from .common import PACKAGE, has_crosscheck, stage_prompt, digest, fingerprint, implementation_hash, lock, now, read, safe_id, write
from .config import load
from .pdf import extract
from .provider import call, identity
from .reuse import import_page_job


def initialize(config, root):
    settings = config['settings']
    protocol = {'settings': settings, 'implementation_sha256': implementation_hash(), 'version': __version__,
                'python': platform.python_version(), 'pymupdf': pymupdf.__version__, 'jsonschema': __import__('importlib.metadata', fromlist=['version']).version('jsonschema')}
    path = root/'protocol.json'
    if path.exists():
        if read(path)['fingerprint'] != fingerprint(protocol):
            raise ValueError('Frozen protocol changed (code, prompts, settings or environment); use a new run ID')
    else:
        write(path, {'fingerprint': fingerprint(protocol), 'protocol': protocol, 'created': now()})
    cohort_path = root/'cohort.json'
    cohort = read(cohort_path) if cohort_path.exists() else {}
    new = {p['id']: {**p, 'documents': [{**d, 'sha256': digest(d['path'])} for d in p['documents']]} for p in config['papers']}
    for key, old in cohort.items():
        if key not in new or new[key] != old:
            raise ValueError('Existing cohort membership/metadata/input changed: ' + key + '; use a new run ID')
    write(cohort_path, new)


def source_ids(sources):
    return {s['id'] for p in sources['pages'] for s in p['blocks'] + p['images']}


def select_blocks(pages, budget, predicate=lambda p: True):
    selected, omitted = [], []
    remaining = budget
    for page in pages:
        if not predicate(page):
            continue
        for b in page['blocks']:
            item = '[' + b['id'] + '] ' + b['text']
            if len(item) <= remaining:
                selected.append(item)
                remaining -= len(item)
            else:
                omitted.append(b['id'])
    return '\n\n'.join(selected), omitted


def method_context(sources, settings):
    pages = sources['pages']
    explicit = lambda p: p['role_hint'] in {'methods_hint', 'methods_candidate'}
    text, omitted = select_blocks(pages, settings['method_text_chars'], explicit)
    # Include method-like original blocks outside suggested methods pages, within remaining space.
    import re
    candidates = []
    for p in pages:
        if not explicit(p):
            blocks = [b for b in p['blocks'] if re.search(r'\b(replicat|randomi[sz]|blind|statistic|biological repeat|sample size|standard deviation|standard error|p.value|methods?)\b', b['text'], re.I)]
            candidates.append({**p, 'blocks': blocks[:settings['method_blocks_per_page']]})
            omitted.extend(b['id'] for b in blocks[settings['method_blocks_per_page']:])
    more, missed = select_blocks(candidates, max(0, settings['method_text_chars']-len(text)))
    return text + '\n\n' + more, omitted + missed


def inventory(sources):
    return [{'page': p['id'], 'pdf_page': p['pdf_page'], 'printed_label': p['page_label'], 'role_hint': p['role_hint'],
             'text_sources': [b['id'] for b in p['blocks']], 'image_sources': [i['id'] for i in p['images']],
             'caption_candidates': p['caption_candidates'], 'figure_mentions': p.get('figure_mentions', [])} for p in sources['pages']]


def page_prompt(page, sources, settings):
    methods, omitted_methods = method_context(sources, settings)
    text, omitted = select_blocks([page], settings['page_text_chars'])
    labels = {m['label'] for m in page.get('figure_mentions', [])} | {c['label'] for c in page['caption_candidates']}
    # Separate legend pages often have multiple text blocks and figure images may
    # contain no extractable figure number. Supply candidates without claiming a
    # semantic match; never drop continuation blocks merely because they lack a heading.
    caption_ids = set()
    all_captions = not labels
    for source_page in sources['pages']:
        starts = {c['source']: c['label'] for c in source_page['caption_candidates']}
        include = False
        for block in source_page['blocks']:
            if block['id'] in starts:
                include = all_captions or starts[block['id']] in labels
            if include:
                caption_ids.add(block['id'])
    related_pages = [{**p, 'blocks': [b for b in p['blocks'] if b['id'] in caption_ids]} for p in sources['pages'] if p['id'] != page['id']]
    captions, omitted_captions = select_blocks(related_pages, 12000)
    evidence = {'target_page': page['id'], 'target_pdf_page': page['pdf_page'], 'page_label': page['page_label'],
                'role_hint': page['role_hint'], 'images_in_order': page['images'],
                'caption_candidates': page['caption_candidates'],
                'document_inventory': inventory(sources),
                'omitted_target_text_blocks': omitted, 'omitted_method_blocks': omitted_methods,
                'omitted_related_caption_blocks': omitted_captions,
                'caption_link_status': ('unlinked legend candidates because no figure number was extracted; inspect the images to assess relevance' if all_captions else 'label-matched candidates with possible continuation blocks; human verification required')}
    prompt = stage_prompt('page', settings) + '\n\nSOURCE MAP\n' + json.dumps(evidence, ensure_ascii=False) + '\n\nTARGET ORIGINAL TEXT\n' + text + '\n\nORIGINAL METHODS CONTEXT\n' + methods + '\n\nRELATED ORIGINAL CAPTION CANDIDATES\n' + captions
    return prompt


def crosscheck_prompt(sources, settings):
    text, omitted = select_blocks(sources['pages'], settings['crosscheck_text_chars'], lambda p: p['role_hint'] not in {'references_candidate', 'resources'})
    coverage = {'omitted_blocks': omitted, 'images': 'No images are supplied to this stage.', 'warnings': sources['warnings']}
    return (stage_prompt('crosscheck', settings) + '\n\nORIGINAL TEXT OF ALL SUPPLIED DOCUMENTS\n' + text +
            '\n\nCONTEXT COVERAGE\n' + json.dumps(coverage, ensure_ascii=False)), omitted


def compact(text):
    """Quotes, dashes and whitespace differ between PDF extraction and model output; compare without them."""
    return re.sub(r'[\s"\'`\u2018\u2019\u201c\u201d\u00b4]+', '', text).replace('\u2013', '-').replace('\u2014', '-').lower()


def verify_quotes(result, sources):
    """Check by code that every quote occurs verbatim (ignoring quotes, dashes and whitespace) in the cited document.

    Source blocks are often single lines, so a sentence can span consecutive blocks or a page break. A quote counts as verified when
    all its segments are found in the document text and at least one overlaps the cited block."""
    pages, documents = {}, {}
    for page in sources['pages']:
        documents.setdefault(page['document'], []).append(page)
    for pages_of_document in documents.values():
        text, spans = '', {}
        for page in pages_of_document:
            for block in page['blocks']:
                if re.fullmatch(r'\s*\d{1,4}\s*', block['text']):
                    continue  # bare page number between pages
                piece = compact(block['text'])
                spans[block['id']] = (len(text), len(text) + len(piece))
                text += piece
        for block_id in spans:
            pages[block_id] = (text, spans)
    def verified(passage):
        segments = [s for s in (compact(part) for part in re.split(r'\.\.\.|\u2026', passage['quote'])) if s]
        if not segments or passage['source'] not in pages:
            return False
        text, spans = pages[passage['source']]
        start, end = spans[passage['source']]
        overlaps = False
        for segment in segments:
            found = False
            at = text.find(segment)
            while at >= 0:
                found = True
                overlaps = overlaps or (at < end and at + len(segment) > start)
                at = text.find(segment, at + 1)
            if not found:
                return False
        return overlaps
    return {**result, 'checks': [{**check, 'passages': [{**p, 'quote_verified': verified(p)} for p in check['passages']]} for check in result['checks']]}


def review_prompt(sources, settings, pages, crosscheck=None):
    methods, omitted_methods = method_context(sources, settings)
    required = '\n\nPAGE EVIDENCE RECORDS (MODEL OUTPUTS, NOT GROUND TRUTH)\n' + json.dumps(pages, ensure_ascii=False)
    required += '\n\nCOMPLETE SOURCE INVENTORY (NOT ALL SOURCE CONTENT IS IN THIS PROMPT)\n' + json.dumps(inventory(sources), ensure_ascii=False)
    required += '\n\nORIGINAL METHODS CONTEXT\n' + methods
    if crosscheck is not None:
        required += '\n\nCROSS-CHECK FINDINGS (MODEL OUTPUT; quote_verified is set by code that searched the cited original block)\n' + json.dumps(crosscheck, ensure_ascii=False)
    if len(required) > settings['review_text_chars']:
        raise ValueError('Mandatory review context exceeds review_text_chars. No evidence silently dropped; use a new protocol with a larger context budget')
    original, omitted_original = select_blocks(sources['pages'], settings['review_text_chars']-len(required), lambda p: p['role_hint'] not in {'references_candidate', 'resources'})
    return stage_prompt('review', settings) + required + '\n\nADDITIONAL ORIGINAL TEXT\n' + original + '\n\nCONTEXT COVERAGE\n' + json.dumps({'omitted_method_blocks': omitted_methods,
        'original_text_blocks_not_repeated_in_additional_context': omitted_original,
        'images': 'Images were inspected in page stages. No images are attached to this synthesis; page assessments can be wrong.',
        'warnings': sources['warnings']}, ensure_ascii=False)


def render_report(root):
    cohort = read(root/'cohort.json')
    lines = ['# Local scientific review batch', '', 'Model-generated interpretations require human scientific review. Operational completion does not certify correctness.', '']
    for pid, paper in cohort.items():
        directory = root/'papers'/pid
        lines.extend(['## ' + pid, '', 'Exploratory: ' + str(paper.get('exploratory', False)), ''])
        status = read(directory/'status.json') if (directory/'status.json').exists() else {'status': 'not_started'}
        lines.extend(['Status: ' + status['status'], ''])
        if status.get('error'):
            lines.extend(['Operational error: ' + status['error'], ''])
        review_path = directory/'review.json'
        if not review_path.exists():
            continue
        review = read(review_path)
        lines.extend([review['scope'], '', review['overall_assessment'], ''])
        for claim in review['major_claims']:
            lines.extend(['### ' + claim['id'] + ': ' + claim['authors_claim'], '',
                'Evidence: ' + claim['evidence_strength'] + '. Interpretation: ' + claim['interpretation_status'] + '.', '',
                claim['assessment'], '', claim['strength_rationale'], '', 'Causal scope: ' + claim['causal_scope'], '',
                'Necessity: ' + claim['necessity'] + '; sufficiency: ' + claim['sufficiency'] + '.', '',
                'Sources: ' + ', '.join(claim['sources']), ''])
        cross_path = directory/'crosscheck.json'
        if cross_path.exists():
            cross = read(cross_path)
            lines.extend(['### Cross-check of passages', '', 'Quotes are marked by code as found verbatim in the cited block (verified) or not (unverified).', ''])
            for check in cross['checks']:
                lines.extend([f"- [{check['relation']}] {check['category']}: {check['topic']}. {check['explanation']} Consequence: {check['consequence']}"] +
                    [f"  - {'verified' if p['quote_verified'] else 'UNVERIFIED'} {p['source']}: {p['quote']}" for p in check['passages']] + [''])
            if not cross['checks']:
                lines.extend(['- No cross-passage findings reported.', ''])
            lines.extend(['Not checked: ' + '; '.join(cross['not_checked']) if cross['not_checked'] else 'Not checked: nothing listed.', ''])
        for key in ('hypotheses', 'scientific_practice', 'claim_measurement_links', 'reporting_and_statistics', 'triangulation', 'validation_gaps'):
            if key not in review:
                continue
            lines.extend(['### ' + key.replace('_', ' ').title(), ''])
            for item in review[key]:
                lines.extend(['- ' + '; '.join(f'{k}: {json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v}' for k, v in item.items()), ''])
        lines.extend(['### Context limitations', ''] + ['- ' + item for item in review['context_limitations']] + [''])
    (root/'report.md').write_text('\n'.join(lines), encoding='utf-8')


def execute(manifest, run_id, runs, *, prepare=False, paper_ids=None, max_page_jobs=None, retry_failed=False, reuse_completed_from=None):
    config = load(manifest)
    root = Path(runs).resolve()/safe_id(run_id)
    with lock(root):
        initialize(config, root)
        plan_path = root/'reuse_plan.json'
        if plan_path.exists():
            saved = read(plan_path)['source_run']
            if reuse_completed_from and str(Path(reuse_completed_from).resolve()) != saved:
                raise ValueError('Reuse origin changed; choose a new run ID')
            reuse_completed_from = saved
        elif reuse_completed_from:
            reuse_completed_from = str(Path(reuse_completed_from).resolve())
            if Path(reuse_completed_from) == root:
                raise ValueError('Cannot import a run into itself')
            write(plan_path, {'source_run': reuse_completed_from, 'created': now(),
                'scope': 'Completed page calls only; exact context/model/images checked. Failed attempts remain at origin. Original output settings retained per imported call.'})
        papers = config['papers']
        if paper_ids:
            unknown = set(paper_ids)-{p['id'] for p in papers}
            if unknown:
                raise ValueError('Unknown paper IDs: ' + ', '.join(sorted(unknown)))
            papers = [p for p in papers if p['id'] in paper_ids]
        jobs, errors = 0, []
        provider = None
        if not prepare:
            provider = identity(config['settings'])
            path = root/'provider.json'
            if path.exists() and read(path) != provider:
                raise ValueError('Ollama version/model digest changed; choose a new run ID')
            if reuse_completed_from and read(Path(reuse_completed_from)/'provider.json') != provider:
                raise ValueError('Imported run uses a different provider/model identity')
            write(path, provider)
        for paper in papers:
            directory = root/'papers'/paper['id']
            try:
                sources = extract(paper, directory/'sources', config['settings'])
                if prepare:
                    if not (directory/'status.json').exists():
                        write(directory/'status.json', {'status': 'prepared', 'pages': len(sources['pages'])})
                    continue
                write(directory/'status.json', {'status': 'running', 'started': now()})
                results = []
                methods, _ = method_context(sources, config['settings'])
                for page in sources['pages']:
                    stage = directory/'page_jobs'/page['id']
                    if reuse_completed_from:
                        import_page_job(Path(reuse_completed_from)/'papers'/paper['id']/'page_jobs'/page['id'], stage, reuse_completed_from)
                    successful = any((p/'state.json').exists() and read(p/'state.json')['status'] == 'complete' for p in stage.glob('attempt_*'))
                    if not successful and max_page_jobs is not None and jobs >= max_page_jobs:
                        write(directory/'status.json', {'status': 'paused_page_limit', 'page_results': len(results), 'total_pages': len(sources['pages'])})
                        break
                    result = call(stage, stage='page', prompt=page_prompt(page, sources, config['settings']),
                        images=[directory/'sources'/i['path'] for i in page['images']], source_ids=source_ids(sources),
                        settings=config['settings'], retry_failed=retry_failed)
                    if result['page_id'] != page['id']:
                        # Keep the scientific response; attribution mismatch is a warning for human review.
                        write(stage/'attribution_warning.json', {'expected_page': page['id'], 'returned_page': result['page_id']})
                    results.append(result)
                    if not successful:
                        jobs += 1
                if len(results) != len(sources['pages']):
                    continue
                crosscheck = None
                if has_crosscheck(config['settings']):
                    prompt, omitted = crosscheck_prompt(sources, config['settings'])
                    found = call(directory/'crosscheck_job', stage='crosscheck', prompt=prompt, images=[], source_ids=source_ids(sources),
                        settings=config['settings'], retry_failed=retry_failed)
                    crosscheck = verify_quotes(found, sources)
                    write(directory/'crosscheck.json', crosscheck)
                    write(directory/'crosscheck_coverage.json', {'omitted_blocks': omitted})
                result = call(directory/'review_job', stage='review', prompt=review_prompt(sources, config['settings'], results, crosscheck),
                    images=[], source_ids=source_ids(sources), settings=config['settings'], retry_failed=retry_failed)
                write(directory/'review.json', result)
                write(directory/'status.json', {'status': 'complete', 'ended': now(), 'pages': len(results), 'scientific_accuracy': 'unverified'})
            except Exception as exc:
                write(directory/'status.json', {'status': 'failed', 'ended': now(), 'error': str(exc)})
                errors.append({'paper': paper['id'], 'error': str(exc)})
        render_report(root)
        write(root/'last_execution.json', {'ended': now(), 'new_page_jobs': jobs, 'errors': errors, 'prepare_only': prepare})
        return root, errors
