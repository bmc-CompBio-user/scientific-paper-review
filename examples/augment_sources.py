"""Review added PDF documents, then synthesize both source packages explicitly.

Earlier page records are inputs from an earlier context, never cache hits under
changed scientific inputs. The orchestration file itself is fingerprinted.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import shutil
import time
import jsonschema
from scientific_review.common import PACKAGE, digest, fingerprint, lock, now, read, safe_id, write
from scientific_review.config import load
from scientific_review.pdf import extract
from scientific_review.pipeline import initialize, page_prompt, review_prompt, source_ids, render_report
from scientific_review.provider import call, identity
from scientific_review.reuse import import_page_job

UPDATE_NOTE = '''SOURCE-PACKAGE UPDATE
The input records identify their analysis context in _analysis_provenance. Earlier-context records were generated before the added documents were supplied. They are preserved provisional observations, not fresh page analyses with the expanded source package. The original text, methods and newly analysed pages are now available for the combined assessment. Reassess earlier missing-context statements and validation-gap claims against the expanded supplied material; do not carry them forward as established study-wide absences. This is the same study with additional sources, not independent replication. Preserve uncertainty if the expanded evidence does not resolve a question.
'''


def unchanged_prior_pages(prior_sources, current_sources):
    """Reject removed/altered source documents or altered page representations."""
    current_docs = {d['id']: d for d in current_sources['documents']}
    for old in prior_sources['documents']:
        current = current_docs.get(old['id'])
        if current is None or current['sha256'] != old['sha256']:
            raise ValueError('An earlier source document was removed or changed: ' + old['id'])
    current_pages = {p['id']: p for p in current_sources['pages']}
    for page in prior_sources['pages']:
        if page['id'] not in current_pages or fingerprint(current_pages[page['id']]) != fingerprint(page):
            raise ValueError('An earlier page representation changed: ' + page['id'])
    return {p['id'] for p in prior_sources['pages']}


def prior_record(prior_paper, page):
    attempts = sorted((prior_paper/'page_jobs'/page['id']).glob('attempt_*'))
    if not attempts or read(attempts[-1]/'state.json')['status'] != 'complete':
        raise ValueError('Earlier page call incomplete: ' + page['id'])
    attempt = attempts[-1]
    request = read(attempt/'request.json')
    response = read(attempt/'response.json')
    result = read(attempt/'result.json')
    if not response.get('done') or response.get('done_reason') != 'stop' or json.loads(response['message']['content']) != result:
        raise ValueError('Earlier result differs from a normally completed response: ' + page['id'])
    images = request['messages'][1].pop('images', [])
    hashes = [hashlib.sha256(base64.b64decode(im, validate=True)).hexdigest() for im in images]
    expected = [im['sha256'] for im in page['images']]
    if hashes != expected:
        raise ValueError('Earlier request images do not match earlier sources: ' + page['id'])
    if fingerprint({'payload': request, 'images': hashes}) != read(attempt/'input.json')['fingerprint']:
        raise ValueError('Earlier request input fingerprint changed: ' + page['id'])
    jsonschema.validate(result, read(PACKAGE/'schemas/page.json'))
    proof = {'origin_attempt': str(attempt.resolve()),
        'request_sha256': digest(attempt/'request.json'), 'response_sha256': digest(attempt/'response.json'),
        'result_sha256': digest(attempt/'result.json'), 'source_page': page['id'],
        'original_options': request['options'], 'images_supplied': len(images)}
    return result, proof


def augment(manifest, run_id, prior_run, runs='data/runs', paper_id=None, retry_failed=False, reuse_added_pages_from=None):
    config = load(manifest)
    papers = config['papers']
    if paper_id:
        papers = [p for p in papers if p['id'] == paper_id]
    if len(papers) != 1:
        raise ValueError('Select exactly one paper for source augmentation')
    paper = papers[0]
    prior_run = Path(prior_run).resolve()
    root = Path(runs).resolve()/safe_id(run_id)
    if root == prior_run:
        raise ValueError('The expanded source package requires a new run ID')
    prior_paper = prior_run/'papers'/paper['id']
    directory = root/'papers'/paper['id']
    started = time.monotonic()
    with lock(root):
        initialize(config, root)
        if reuse_added_pages_from:
            reuse_added_pages_from = str(Path(reuse_added_pages_from).resolve())
            if Path(reuse_added_pages_from) == root:
                raise ValueError('Cannot import current-context page calls from the target run itself')
        policy = {'mode': 'source_augmentation', 'prior_run': str(prior_run),
            'reuse_added_pages_from': reuse_added_pages_from,
            'orchestration_sha256': digest(Path(__file__).resolve()),
            'policy': 'Earlier page records retain their earlier source context; only added pages are newly analysed. All source text and records enter a fresh combined synthesis. This is not exact-context cache reuse or an independent study.'}
        policy_path = root/'augmentation.json'
        if policy_path.exists() and read(policy_path) != policy:
            raise ValueError('Augmentation origin or orchestration changed; choose a new run ID')
        write(policy_path, policy)
        snapshot = root/'orchestration.py'
        if not snapshot.exists():
            shutil.copy2(Path(__file__).resolve(), snapshot)
        sources = extract(paper, directory/'sources', config['settings'])
        old_sources = read(prior_paper/'sources/sources.json')
        old_ids = unchanged_prior_pages(old_sources, sources)
        added = [p for p in sources['pages'] if p['id'] not in old_ids]
        if not added:
            raise ValueError('No additional source pages were supplied')
        provider = identity(config['settings'])
        old_provider = read(prior_run/'provider.json')
        if provider != old_provider:
            raise ValueError('Earlier evidence uses a different provider/model identity')
        if (root/'provider.json').exists() and read(root/'provider.json') != provider:
            raise ValueError('Provider changed within the expanded run')
        write(root/'provider.json', provider)
        if reuse_added_pages_from:
            compatible = Path(reuse_added_pages_from)
            if read(compatible/'provider.json') != provider:
                raise ValueError('Current-context reuse has a different model/provider identity')
            reused_sources = read(compatible/'papers'/paper['id']/'sources/sources.json')
            reused_ids = unchanged_prior_pages(reused_sources, sources)
            if reused_ids != {p['id'] for p in sources['pages']}:
                raise ValueError('Current-context reuse requires the same full source package')
        record_map = {}
        proofs = []
        for page in old_sources['pages']:
            value, proof = prior_record(prior_paper, page)
            prior_path = directory/'prior_evidence'/page['id']
            if (prior_path/'provenance.json').exists() and read(prior_path/'provenance.json') != proof:
                raise ValueError('Prior evidence changed since augmentation began')
            write(prior_path/'result.json', value)
            write(prior_path/'provenance.json', proof)
            record_map[page['id']] = {**value, '_analysis_provenance': {
                'context': 'earlier source package; added documents were not supplied',
                'origin_run': str(prior_run), 'source_document_ids': [d['id'] for d in old_sources['documents']],
                'fresh_analysis_with_expanded_package': False}}
            proofs.append(proof)
        write(directory/'prior_evidence_manifest.json', {'prior_sources': old_sources['documents'], 'pages': proofs})
        print(f'Validated {len(old_ids)} earlier page records; {len(added)} added pages require new analysis.', flush=True)
        try:
            write(directory/'status.json', {'status': 'running', 'started': now(), 'mode': 'source_augmentation',
                'prior_page_records': len(old_ids), 'new_page_analyses': 0, 'total_source_pages': len(sources['pages'])})
            for index, page in enumerate(added, 1):
                print(f'Added page {index}/{len(added)}: {page["id"]}', flush=True)
                if reuse_added_pages_from:
                    import_page_job(Path(reuse_added_pages_from)/'papers'/paper['id']/'page_jobs'/page['id'],
                                    directory/'page_jobs'/page['id'], reuse_added_pages_from)
                value = call(directory/'page_jobs'/page['id'], stage='page',
                    prompt=page_prompt(page, sources, config['settings']),
                    images=[directory/'sources'/im['path'] for im in page['images']],
                    source_ids=source_ids(sources), settings=config['settings'], retry_failed=retry_failed)
                if value['page_id'] != page['id']:
                    write(directory/'page_jobs'/page['id']/'attribution_warning.json', {'expected_page': page['id'], 'returned_page': value['page_id']})
                record_map[page['id']] = {**value, '_analysis_provenance': {
                    'context': 'expanded source package', 'source_document_ids': [d['id'] for d in sources['documents']],
                    'fresh_analysis_with_expanded_package': True}}
                write(directory/'status.json', {'status': 'running', 'mode': 'source_augmentation',
                    'prior_page_records': len(old_ids), 'new_page_analyses': index, 'total_source_pages': len(sources['pages'])})
            records = [record_map[p['id']] for p in sources['pages']]
            write(directory/'synthesis-evidence.json', records)
            prompt = UPDATE_NOTE + '\n\n' + review_prompt(sources, config['settings'], records)
            print('Generating fresh combined whole-study assessment.', flush=True)
            result = call(directory/'review_job', stage='review', prompt=prompt, images=[], source_ids=source_ids(sources),
                          settings=config['settings'], retry_failed=retry_failed)
            write(directory/'review.json', result)
            write(directory/'status.json', {'status': 'complete', 'ended': now(), 'mode': 'source_augmentation',
                'prior_page_records': len(old_ids), 'new_page_analyses': len(added), 'total_source_pages': len(sources['pages']),
                'scientific_accuracy': 'unverified', 'independent_study': False})
            errors = []
        except Exception as exc:
            write(directory/'status.json', {'status': 'failed', 'ended': now(), 'error': str(exc), 'mode': 'source_augmentation'})
            errors = [{'paper': paper['id'], 'error': str(exc)}]
        render_report(root)
        write(root/'last_execution.json', {'ended': now(), 'mode': 'source_augmentation', 'errors': errors,
              'wall_seconds_this_execution': time.monotonic()-started})
        return root, errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest')
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--prior-run', required=True)
    parser.add_argument('--runs', default='data/runs')
    parser.add_argument('--paper')
    parser.add_argument('--retry-failed', action='store_true')
    parser.add_argument('--reuse-added-pages-from', help='Earlier run with identical expanded-context page inputs; all reuse is verified')
    args = parser.parse_args()
    root, errors = augment(args.manifest, args.run_id, args.prior_run, args.runs, args.paper, args.retry_failed, args.reuse_added_pages_from)
    print(json.dumps({'run': str(root), 'errors': errors}, indent=2))
    raise SystemExit(1 if errors else 0)
