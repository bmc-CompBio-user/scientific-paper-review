"""Auditable Ollama HTTP calls. Scientific quality flags never erase a response."""
import base64
import copy
import json
import time
import urllib.error
import urllib.request
import jsonschema
from .common import PACKAGE, stage_schema, digest, now, read, write, fingerprint
from .reuse import verify_reuse


class OperationalError(RuntimeError):
    pass


def http(host, route, payload=None, timeout=30):
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(host.rstrip('/') + route, data=data,
        headers={'Content-Type': 'application/json'})
    # Ignore HTTP proxy environment variables; never send manuscripts to a proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        return json.load(response)


def identity(settings):
    tags = http(settings['host'], '/api/tags')
    matches = [m for m in tags.get('models', []) if m.get('name') == settings['model'] or m.get('model') == settings['model']]
    if len(matches) != 1 or not matches[0].get('digest'):
        raise OperationalError('Requested model is not installed with an identifiable digest')
    return {'ollama': http(settings['host'], '/api/version'), 'model': matches[0]}


def source_schema(name, source_ids, settings=None):
    schema = copy.deepcopy(read(stage_schema(name, settings or {"rubric": "scientific-method-v1.0.0"})))
    def visit(node):
        if isinstance(node, dict):
            if name == 'review' and node.get('type') == 'array':
                node.setdefault('maxItems', 8)
            for key, value in list(node.items()):
                if key == 'sources' and isinstance(value, dict):
                    value['items'] = {'type': 'string', 'enum': sorted(source_ids)}
                    value['maxItems'] = 8
                else:
                    visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)
    visit(schema)
    return schema


TRAILING_WORDS = {'a', 'an', 'the', 'of', 'to', 'in', 'on', 'for', 'by', 'with', 'as', 'at', 'from', 'that', 'which', 'and', 'or', 'but', 'than', 'like'}


def looks_truncated(text):
    """A text value that stops mid-sentence, as when an unescaped quote ends a constrained-decoding string."""
    stripped = text.rstrip()
    if not stripped:
        return False
    return text != stripped or stripped[-1] in '(:,;' or stripped.split()[-1].lower() in TRAILING_WORDS


def quality_flags(value, source_ids, stage):
    flags = []
    def visit(node, location='$'):
        if isinstance(node, dict):
            for key, item in node.items():
                loc = location + '.' + key
                if key == 'sources' and isinstance(item, list):
                    if not item:
                        flags.append({'kind': 'empty_sources', 'location': loc})
                    for ref in item:
                        if ref not in source_ids:
                            flags.append({'kind': 'unknown_source', 'location': loc, 'source': ref})
                else:
                    visit(item, loc)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                visit(item, f'{location}[{index}]')
        elif isinstance(node, str) and looks_truncated(node):
            flags.append({'kind': 'suspected_truncated_text', 'location': location, 'ends_with': node[-40:]})
    visit(value)
    if stage == 'review':
        ids = [c['id'] for c in value['major_claims']]
        if len(ids) != len(set(ids)):
            flags.append({'kind': 'duplicate_claim_ids'})
        for category in ('triangulation', 'validation_gaps'):
            for item in value[category]:
                if item['claim_id'] not in ids:
                    flags.append({'kind': 'unknown_claim_link', 'category': category, 'claim_id': item['claim_id']})
    return flags


def call(folder, *, stage, prompt, images, source_ids, settings, retry_failed=False, transport=http):
    folder.mkdir(parents=True, exist_ok=True)
    schema = source_schema(stage, source_ids, settings)
    # Structural validation is separate from citation consistency warnings.
    basic_schema = read(stage_schema(stage, settings))
    payload = {'model': settings['model'], 'stream': False, 'think': False, 'format': schema,
        'messages': [{'role': 'system', 'content': (PACKAGE / 'prompts' / (settings['rubric'] + '.md')).read_text()},
                     {'role': 'user', 'content': prompt}],
        'options': {'temperature': settings['temperature'], 'seed': settings['seed'],
                    'num_ctx': settings['num_ctx'], 'num_predict': settings[stage + '_num_predict']}}
    input_identity = fingerprint({'payload': payload, 'images': [digest(p) for p in images]})
    attempts = sorted(folder.glob('attempt_*'))
    if attempts:
        previous = attempts[-1]
        state = read(previous / 'state.json') if (previous/'state.json').exists() else {'status': 'interrupted'}
        if state['status'] == 'complete' and (folder/'reuse.json').exists():
            return verify_reuse(folder, previous, payload, [digest(p) for p in images], source_ids)
        if (previous/'input.json').exists() and read(previous/'input.json')['fingerprint'] != input_identity:
            raise OperationalError('Stage inputs changed; choose a new run ID')
        if state['status'] == 'complete':
            return read(previous/'result.json')
        if not retry_failed:
            raise OperationalError('Failed/interrupted attempt retained. Use --retry-failed to create a new attempt')
    attempt = folder / f'attempt_{len(attempts)+1:03d}'
    attempt.mkdir()
    write(attempt/'input.json', {'fingerprint': input_identity, 'source_ids': sorted(source_ids),
                                'image_sha256': [digest(p) for p in images]})
    (attempt/'prompt.txt').write_text(prompt, encoding='utf-8')
    if images:
        payload['messages'][1]['images'] = [base64.b64encode(p.read_bytes()).decode('ascii') for p in images]
    write(attempt/'request.json', payload)
    write(attempt/'state.json', {'status': 'running', 'started': now()})
    started = time.monotonic()
    try:
        response = transport(settings['host'], '/api/chat', payload, settings['timeout_seconds'])
        write(attempt/'response.json', response)
        if not response.get('done') or response.get('done_reason') != 'stop':
            raise OperationalError('Response incomplete or token limit reached: ' + str(response.get('done_reason')))
        value = json.loads(response['message']['content'])
        jsonschema.validate(value, basic_schema)
        flags = quality_flags(value, source_ids, stage)
        write(attempt/'quality_flags.json', flags)
        write(attempt/'result.json', value)
        write(attempt/'state.json', {'status': 'complete', 'ended': now(), 'wall_seconds': time.monotonic()-started,
            'quality_flag_count': len(flags), 'metrics': {k: response[k] for k in (
                'total_duration', 'load_duration', 'prompt_eval_count', 'prompt_eval_duration', 'eval_count', 'eval_duration') if k in response}})
        return value
    except Exception as exc:
        write(attempt/'state.json', {'status': 'failed', 'ended': now(), 'wall_seconds': time.monotonic()-started,
              'error_type': type(exc).__name__, 'error': str(exc)})
        raise OperationalError(f'{stage} failed; saved attempt at {attempt}: {exc}') from exc
