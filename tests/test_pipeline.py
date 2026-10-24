import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pymupdf
from scientific_review.common import PACKAGE, read, write
from scientific_review.config import DEFAULTS, load
from scientific_review.evaluation import evaluate
from scientific_review.pdf import extract
from scientific_review.pipeline import execute, review_prompt, page_prompt
from scientific_review.provider import call, OperationalError, quality_flags, source_schema
from scientific_review.reuse import import_page_job


def pdf(path):
    document = pymupdf.open()
    page = document.new_page(width=400, height=500)
    page.insert_textbox((30, 30, 370, 230), 'SYNTHETIC STUDY. Figure 1. Inhibition of X lowers reporter Y.\nA rescue restores Y. Three independent cultures per group.\nThe authors hypothesize direct regulation; no binding assay is reported.', fontsize=12)
    page.draw_rect((70, 300, 130, 430), color=(0, 0, 0), fill=(0.2, 0.4, 0.8))
    page.draw_rect((180, 370, 240, 430), color=(0, 0, 0), fill=(0.8, 0.4, 0.2))
    page.insert_text((70, 455), 'Control           Inhibited')
    page = document.new_page(width=400, height=500)
    page.insert_textbox((30, 30, 370, 450), 'METHOD DETAILS\nCultures were randomly allocated to control, inhibitor, or rescue.\nThree independent cultures per group, technical triplicates averaged.\nReporter fluorescence measured after 24 hours.\nThe rescue uses an inhibitor-resistant X construct.\nNo direct binding or transcription measurement was performed.\nSynthetic fixture for software testing, not real scientific data.', fontsize=12)
    document.save(path)
    document.close()


def blank(schema):
    if 'enum' in schema:
        return schema['enum'][0]
    kind = schema.get('type')
    if kind == 'object':
        return {k: blank(v) for k, v in schema['properties'].items()}
    if kind == 'array':
        return []
    if kind == 'boolean':
        return False
    if kind in ('number', 'integer'):
        return 0
    return 'Synthetic fixture'


def review_value():
    value = blank(read(PACKAGE/'schemas/review.json'))
    claim = blank(read(PACKAGE/'schemas/review.json')['properties']['major_claims']['items'])
    claim['id'] = 'C1'
    value['major_claims'] = [claim]
    return value


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        pdf(self.root/'input.pdf')
        self.manifest = self.root/'batch.json'
        write(self.manifest, {'settings': {'dpi': 100, 'tiles': False}, 'papers': [{'id': 's1', 'independence_group': 'study1',
            'documents': [{'id': 'main', 'path': 'input.pdf', 'method_pages': [2]}]}]})
        self.config = load(self.manifest)

    def test_sources_and_supplement_identity(self):
        paper = copy.deepcopy(self.config['papers'][0])
        paper['documents'].append({'id': 'supp', 'path': str(self.root/'input.pdf')})
        result = extract(paper, self.root/'sources', self.config['settings'])
        self.assertEqual(len(result['pages']), 4)
        ids = [p['id'] for p in result['pages']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(result['pages'][1]['role_hint'], 'methods_hint')
        self.assertEqual(extract(paper, self.root/'sources', self.config['settings']), result)
        image = self.root/'sources'/result['pages'][0]['images'][0]['path']
        image.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'Cached image'):
            extract(paper, self.root/'sources', self.config['settings'])

    def test_unlabelled_figure_gets_separate_legend_continuations(self):
        sources = extract(self.config['papers'][0], self.root/'sources', self.config['settings'])
        figure = sources['pages'][0]
        figure['figure_mentions'] = []
        figure['caption_candidates'] = []
        legend = sources['pages'][1]
        legend['caption_candidates'] = [{'source': 'main.p002.b100', 'label': 'Figure 1'}]
        legend['blocks'] = [{'id': 'main.p002.b100', 'text': 'Figure 1. Legend starts.'},
                            {'id': 'main.p002.b101', 'text': 'Continuation: independent cultures and error-bar definition.'}]
        prompt = page_prompt(figure, sources, self.config['settings'])
        supplied = prompt.split('RELATED ORIGINAL CAPTION CANDIDATES\n')[-1]
        self.assertIn('main.p002.b101', supplied)
        self.assertIn('independent cultures', supplied)
        self.assertIn('unlinked legend candidates', prompt)
        figure['figure_mentions'] = [{'label': 'Figure 2'}]
        prompt = page_prompt(figure, sources, self.config['settings'])
        self.assertEqual(prompt.split('RELATED ORIGINAL CAPTION CANDIDATES\n')[-1], '')

    def test_local_only_and_no_thinking(self):
        for setting in ({'host': 'http://example.com'}, {'think': True}):
            manifest = read(self.manifest)
            manifest.setdefault('settings', {}).update(setting)
            write(self.manifest, manifest)
            with self.assertRaises(Exception):
                load(self.manifest)
            write(self.manifest, {'papers': self.config['papers']})

    def test_frozen_protocol_and_append_only_cohort(self):
        root, errors = execute(self.manifest, 'r1', self.root/'runs', prepare=True)
        self.assertFalse(errors)
        manifest = read(self.manifest)
        manifest['papers'].append({'id': 's2', 'documents': [{'id': 'main', 'path': 'input.pdf'}]})
        write(self.manifest, manifest)
        execute(self.manifest, 'r1', self.root/'runs', prepare=True)
        manifest['papers'] = manifest['papers'][1:]
        write(self.manifest, manifest)
        with self.assertRaisesRegex(ValueError, 'cohort'):
            execute(self.manifest, 'r1', self.root/'runs', prepare=True)
        manifest['papers'] = self.config['papers']
        manifest['settings']['seed'] = 5
        write(self.manifest, manifest)
        with self.assertRaisesRegex(ValueError, 'protocol'):
            execute(self.manifest, 'r1', self.root/'runs', prepare=True)

    def test_call_resume_and_quality_warning_retained(self):
        value = blank(read(PACKAGE/'schemas/page.json'))
        value['page_id'] = 'main.p001'
        obs = blank(read(PACKAGE/'schemas/page.json')['properties']['observations']['items'])
        obs['sources'] = ['wrong.source']
        value['observations'] = [obs]
        calls = []
        def transport(*args):
            calls.append(args)
            return {'done': True, 'done_reason': 'stop', 'message': {'content': json.dumps(value)}}
        kwargs = dict(stage='page', prompt='English test', images=[], source_ids={'main.p001.b000'}, settings=DEFAULTS, transport=transport)
        result = call(self.root/'job', **kwargs)
        self.assertEqual(result, value)
        self.assertEqual(call(self.root/'job', **kwargs), value)
        self.assertEqual(len(calls), 1)
        flags = read(self.root/'job/attempt_001/quality_flags.json')
        self.assertEqual(flags[0]['kind'], 'unknown_source')
        self.assertFalse(read(self.root/'job/attempt_001/request.json')['think'])
        with self.assertRaisesRegex(OperationalError, 'inputs changed'):
            call(self.root/'job', **{**kwargs, 'prompt': 'changed'})

    def test_explicit_import_preserves_original_request_and_checks_context(self):
        value = blank(read(PACKAGE/'schemas/page.json'))
        old_schema = source_schema('page', {'main.p001.b000'})
        # The previous protocol did not cap citation arrays.
        old_schema['properties']['observations']['items']['properties']['sources'].pop('maxItems')
        settings = {**DEFAULTS, 'page_num_predict': 4096}
        kwargs = dict(stage='page', prompt='identical original scientific context', images=[], source_ids={'main.p001.b000'}, settings=settings)
        calls = []
        def transport(*args):
            calls.append(args)
            return {'done': True, 'done_reason': 'stop', 'message': {'content': json.dumps(value)}}
        with patch('scientific_review.provider.source_schema', return_value=old_schema):
            call(self.root/'old', **kwargs, transport=transport)
        original = (self.root/'old/attempt_001/request.json').read_bytes()
        import_page_job(self.root/'old', self.root/'new', self.root/'origin-run')
        current = {**kwargs, 'settings': {**settings, 'page_num_predict': 8192}}
        self.assertEqual(call(self.root/'new', **current, transport=transport), value)
        self.assertEqual(len(calls), 1)
        self.assertEqual((self.root/'new/attempt_001/request.json').read_bytes(), original)
        proof = read(self.root/'new/reuse_verified.json')
        self.assertEqual(proof['original_num_predict'], 4096)
        self.assertEqual(proof['current_num_predict'], 8192)
        with self.assertRaisesRegex(ValueError, 'scientific context'):
            call(self.root/'new', **{**current, 'prompt': 'different scientific context'}, transport=transport)
        with self.assertRaisesRegex(ValueError, 'scientific context'):
            call(self.root/'new', **{**current, 'settings': {**current['settings'], 'num_ctx': 8192}}, transport=transport)
        image = self.root/'changed.png'
        image.write_bytes(b'changed image data')
        with self.assertRaisesRegex(ValueError, 'source content'):
            call(self.root/'new', **{**current, 'images': [image]}, transport=transport)
        modified = read(self.root/'new/attempt_001/result.json')
        modified['page_scope'] = 'tampered'
        write(self.root/'new/attempt_001/result.json', modified)
        with self.assertRaisesRegex(ValueError, 'raw response'):
            call(self.root/'new', **current, transport=transport)

    def test_failed_jobs_are_never_imported(self):
        write(self.root/'old/attempt_001/state.json', {'status':'failed'})
        import_page_job(self.root/'old', self.root/'new', self.root/'origin-run')
        self.assertFalse((self.root/'new').exists())

    def test_failed_attempts_preserved_and_explicit_retry(self):
        kwargs = dict(stage='page', prompt='test', images=[], source_ids={'main.p001.b000'}, settings=DEFAULTS)
        for failure in ('length', 'json', 'transport'):
            folder = self.root/failure
            def broken(*args):
                if failure == 'transport':
                    raise TimeoutError('synthetic timeout')
                return {'done': True, 'done_reason': 'length' if failure == 'length' else 'stop', 'message': {'content': 'invalid json'}}
            with self.assertRaises(OperationalError):
                call(folder, **kwargs, transport=broken)
            with self.assertRaisesRegex(OperationalError, 'retry-failed'):
                call(folder, **kwargs, transport=broken)
            good = blank(read(PACKAGE/'schemas/page.json'))
            call(folder, **kwargs, retry_failed=True, transport=lambda *a: {'done': True, 'done_reason': 'stop', 'message': {'content': json.dumps(good)}})
            self.assertEqual(read(folder/'attempt_001/state.json')['status'], 'failed')
            self.assertEqual(read(folder/'attempt_002/state.json')['status'], 'complete')

    def test_full_mocked_workflow_resume_and_context(self):
        def transport(host, route, payload=None, timeout=30):
            if route == '/api/tags':
                return {'models': [{'name': DEFAULTS['model'], 'digest': 'synthetic-digest'}]}
            if route == '/api/version':
                return {'version': 'synthetic'}
            schema = payload['format']
            value = blank(schema)
            if 'page_id' in value:
                value['page_id'] = 'main.p001' if '"target_page": "main.p001"' in payload['messages'][1]['content'] else 'main.p002'
            return {'done': True, 'done_reason': 'stop', 'message': {'content': json.dumps(value)}}
        with patch('scientific_review.provider.http', transport), patch('scientific_review.pipeline.call', side_effect=lambda *a, **k: call(*a, **k, transport=transport)):
            root, errors = execute(self.manifest, 'full', self.root/'runs', max_page_jobs=1)
            self.assertFalse(errors)
            self.assertEqual(read(root/'papers/s1/status.json')['status'], 'paused_page_limit')
            root, errors = execute(self.manifest, 'full', self.root/'runs')
            self.assertFalse(errors)
            self.assertEqual(read(root/'papers/s1/status.json')['status'], 'complete')
            before = list(root.rglob('attempt_*'))
            execute(self.manifest, 'full', self.root/'runs')
            self.assertEqual(before, list(root.rglob('attempt_*')))
            prompt = (root/'papers/s1/review_job/attempt_001/prompt.txt').read_text()
            self.assertIn('inhibitor-resistant', prompt)
            self.assertIn('METHODS CONTEXT', prompt)
            self.assertIn('NOT GROUND TRUTH', prompt)
            self.assertTrue((root/'report.md').exists())
            config = read(self.manifest)
            config['settings']['page_num_predict'] = 8192
            write(self.manifest, config)
            imported_root, errors = execute(self.manifest, 'imported', self.root/'runs', reuse_completed_from=root)
            self.assertFalse(errors)
            self.assertEqual(read(imported_root/'papers/s1/status.json')['status'], 'complete')
            self.assertEqual(len(list(imported_root.glob('papers/s1/page_jobs/*/reuse_verified.json'))), 2)
            self.assertTrue((imported_root/'papers/s1/review_job/attempt_001/result.json').exists())


    def test_context_overflow_is_explicit(self):
        sources = extract(self.config['papers'][0], self.root/'sources', self.config['settings'])
        with self.assertRaisesRegex(ValueError, 'No evidence silently dropped'):
            review_prompt(sources, {**self.config['settings'], 'review_text_chars': 10}, [])

    def test_human_recurrence_counts_independent_studies(self):
        run = self.root/'cohort1'
        cohort = {f'p{i}': {'independence_group': 'same' if i < 2 else f'g{i}', 'exploratory': i == 4} for i in range(5)}
        write(run/'cohort.json', cohort)
        rows = []
        for pid, paper in cohort.items():
            write(run/'papers'/pid/'review.json', review_value())
            rows.append({'paper_id': pid, 'run_id': 'cohort1', 'claim_id': 'C1', 'family': 'causal_overreach',
                'severity': 'material', 'confirmed': True, 'origin': 'model_reasoning', 'independence_group': paper['independence_group'],
                'notes': 'Human verified synthetic annotation', 'source_reference': 'main.p001'})
        annotations = self.root/'annotations.jsonl'
        annotations.write_text('\n'.join(json.dumps(r) for r in rows))
        result = evaluate(annotations, run, self.root/'evaluation.json')
        self.assertEqual(result['families'][0]['count'], 3)
        self.assertTrue(result['families'][0]['recurrence_candidate'])
        self.assertFalse(result['annotations'][-1]['eligible_for_recurrence'])
        rows[2]['confirmed'] = False
        annotations.write_text('\n'.join(json.dumps(r) for r in rows))
        self.assertFalse(evaluate(annotations, run, self.root/'evaluation.json')['families'][0]['recurrence_candidate'])

    def test_dynamic_schema_and_claim_links(self):
        schema = source_schema('review', {'main.p001.b000'})
        self.assertEqual(schema['properties']['major_claims']['items']['properties']['sources']['items']['enum'], ['main.p001.b000'])
        self.assertEqual(schema['properties']['major_claims']['items']['properties']['sources']['maxItems'], 8)
        self.assertEqual(schema['properties']['triangulation']['items']['properties']['evidence_streams']['maxItems'], 8)
        self.assertEqual(schema['properties']['major_claims']['items']['properties']['alternative_explanations']['maxItems'], 8)
        self.assertEqual(schema['properties']['context_limitations']['maxItems'], 8)
        self.assertNotIn('maxItems', source_schema('page', {'main.p001.b000'})['properties']['context_limits'])
        value = review_value()
        gap = blank(schema['properties']['validation_gaps']['items'])
        gap['claim_id'] = 'unknown'
        value['validation_gaps'] = [gap]
        self.assertTrue(any(f['kind'] == 'unknown_claim_link' for f in quality_flags(value, set(), 'review')))


    def test_rubric_v110_schemas_and_prompts(self):
        from scientific_review.common import stage_prompt, stage_schema
        settings = {'rubric': 'scientific-method-v1.1.0'}
        review = source_schema('review', {'main.p001.b000'}, settings)
        for key in ('claim_measurement_links', 'reporting_and_statistics'):
            self.assertIn(key, review['required'])
            self.assertEqual(review['properties'][key]['items']['properties']['sources']['items']['enum'], ['main.p001.b000'])
        page = source_schema('page', {'main.p001.b000'}, settings)['properties']['observations']['items']
        self.assertIn('statistics_reported', page['required'])
        self.assertIn('measurement_target', page['required'])
        self.assertIn('Reporting and statistics', (PACKAGE/'prompts/scientific-method-v1.1.0.md').read_text())
        self.assertIn('claim_measurement_links', stage_prompt('review', settings))
        # v1.0.0 stays untouched
        old = {'rubric': 'scientific-method-v1.0.0'}
        self.assertEqual(stage_schema('review', old).name, 'review.json')
        self.assertNotIn('reporting_and_statistics', read(stage_schema('review', old))['properties'])


    def test_truncated_text_flag_and_v111_rules(self):
        from scientific_review.provider import looks_truncated
        self.assertTrue(looks_truncated('Methods state '))
        self.assertTrue(looks_truncated('The use of the'))
        self.assertFalse(looks_truncated('not stated'))
        self.assertFalse(looks_truncated('The design is adequate.'))
        value = review_value()
        value['context_limitations'] = ['The text uses terms like ']
        self.assertTrue(any(f['kind'] == 'suspected_truncated_text' for f in quality_flags(value, set(), 'review')))
        from scientific_review.common import stage_prompt, stage_schema
        settings = {'rubric': 'scientific-method-v1.1.1'}
        self.assertIn('double quotation', (PACKAGE/'prompts/scientific-method-v1.1.1.md').read_text())
        self.assertIn('double quotation', stage_prompt('page', settings))
        self.assertEqual(stage_schema('review', settings).name, 'review-v1.1.1.json')


    def test_crosscheck_quote_verification_and_schema(self):
        from scientific_review.pipeline import verify_quotes
        sources = {'pages': [{'document': 'main', 'blocks': [{'id': 'main.p001.b000', 'text': 'Cells were treated with 500 ng\nRNA ("single") for 24 h; FDR < 0.1 was used.'}]}]}
        passage = lambda source, quote: {'source': source, 'quote': quote}
        result = {'checks': [{'passages': [passage('main.p001.b000', "treated with 500 ng RNA (single) for 24 h"),
                                           passage('main.p001.b000', 'Cells were ... FDR < 0.1'),
                                           passage('main.p001.b000', 'FDR < 0.05 was used'),
                                           passage('main.p009.b000', 'FDR < 0.1'),
                                           passage('main.p001.b000', '')]}]}
        verified = [p['quote_verified'] for p in verify_quotes(result, sources)['checks'][0]['passages']]
        self.assertEqual(verified, [True, True, False, False, False])
        lines = {'pages': [{'document': 'main', 'blocks': [{'id': 'main.p001.b000', 'text': 'was diluted into tris-'}, {'id': 'main.p001.b001', 'text': 'buffered saline (TBS). Equal amounts'},
                                       {'id': 'main.p001.b002', 'text': 'were blotted. After'}, {'id': 'main.p001.b003', 'text': '15'}]}, {'document': 'main', 'blocks': [{'id': 'main.p002.b000', 'text': 'isolation of RNA. Equal amounts elsewhere.'}]}]}
        spans = {'checks': [{'passages': [passage('main.p001.b001', 'diluted into tris-buffered saline (TBS)'),
                                          passage('main.p001.b002', 'Equal amounts were blotted'),
                                          passage('main.p001.b000', 'Equal amounts were blotted'),
                                          passage('main.p002.b000', 'Equal amounts were blotted'),
                                          passage('main.p002.b000', 'blotted. After isolation of RNA')]}]}
        self.assertEqual([p['quote_verified'] for p in verify_quotes(spans, lines)['checks'][0]['passages']], [True, True, False, False, True])
        numbered = {'pages': [{'document': 'main', 'blocks': [{'id': 'main.p001.b000', 'text': 'cells were exposed to 10 nM DHT for \n305'}, {'id': 'main.p001.b001', 'text': '4 hrs. Mono-nucleosomes \n306'}]}]}
        line_numbers = {'checks': [{'passages': [passage('main.p001.b000', 'exposed to 10 nM DHT for 4 hrs')]}]}
        self.assertTrue(verify_quotes(line_numbers, numbered)['checks'][0]['passages'][0]['quote_verified'])
        schema = source_schema('crosscheck', {'main.p001.b000'}, {'rubric': 'scientific-method-v1.2.0'})
        self.assertEqual(schema['properties']['checks']['items']['properties']['passages']['items']['properties']['source']['enum'], ['main.p001.b000'])
        value = blank(schema)
        value['checks'] = [{**blank(schema['properties']['checks']['items']), 'passages': [passage('wrong.source', 'x')]}]
        self.assertTrue(any(f['kind'] == 'unknown_source' for f in quality_flags(value, {'main.p001.b000'}, 'crosscheck')))

    def test_rubric_v120_runs_crosscheck_before_review(self):
        import re
        def transport(host, route, payload=None, timeout=30):
            if route == '/api/tags':
                return {'models': [{'name': DEFAULTS['model'], 'digest': 'synthetic-digest'}]}
            if route == '/api/version':
                return {'version': 'synthetic'}
            value = blank(payload['format'])
            content = payload['messages'][1]['content']
            if 'page_id' in value:
                value['page_id'] = 'main.p001' if '"target_page": "main.p001"' in content else 'main.p002'
            if 'checks' in value:
                block = re.search(r'\[(main\.p\d+\.b\d+)\] [^\[]*?Three independent cultures per group', content)[1]
                check = blank(payload['format']['properties']['checks']['items'])
                check.update(id='X1', topic='replicates', passages=[{'source': block, 'quote': 'Three independent cultures per group'},
                                                                    {'source': block, 'quote': 'Seven invented cultures per group'}])
                value['checks'] = [check]
            return {'done': True, 'done_reason': 'stop', 'message': {'content': json.dumps(value)}}
        config = read(self.manifest)
        config['settings']['rubric'] = 'scientific-method-v1.2.0'
        write(self.manifest, config)
        with patch('scientific_review.provider.http', transport), patch('scientific_review.pipeline.call', side_effect=lambda *a, **k: call(*a, **k, transport=transport)):
            root, errors = execute(self.manifest, 'cc', self.root/'runs')
            self.assertFalse(errors)
            self.assertEqual(read(root/'papers/s1/status.json')['status'], 'complete')
            cross = read(root/'papers/s1/crosscheck.json')
            self.assertEqual([p['quote_verified'] for p in cross['checks'][0]['passages']], [True, False])
            prompt = (root/'papers/s1/review_job/attempt_001/prompt.txt').read_text()
            self.assertIn('CROSS-CHECK FINDINGS', prompt)
            self.assertIn('"quote_verified": false', prompt)
            report = (root/'report.md').read_text()
            self.assertIn('UNVERIFIED', report)
            before = list(root.rglob('attempt_*'))
            execute(self.manifest, 'cc', self.root/'runs')
            self.assertEqual(before, list(root.rglob('attempt_*')))
        # earlier rubrics make no cross-check call
        config['settings']['rubric'] = 'scientific-method-v1.1.1'
        write(self.manifest, config)
        with patch('scientific_review.provider.http', transport), patch('scientific_review.pipeline.call', side_effect=lambda *a, **k: call(*a, **k, transport=transport)):
            root, errors = execute(self.manifest, 'noc', self.root/'runs')
            self.assertFalse(errors)
            self.assertFalse((root/'papers/s1/crosscheck.json').exists())
            self.assertNotIn('CROSS-CHECK', (root/'papers/s1/review_job/attempt_001/prompt.txt').read_text())


    def test_rubric_v130_adds_inference_design_and_negative_evidence(self):
        from scientific_review.common import stage_prompt, stage_schema, has_crosscheck
        settings = {'rubric': 'scientific-method-v1.3.0'}
        self.assertTrue(has_crosscheck(settings))
        rubric = stage_prompt('scientific-method', settings)
        self.assertIn('1.3.0', rubric)
        self.assertIn('11. Inference design and analysis fit', rubric)
        self.assertIn('12. Negative and absence evidence', rubric)
        self.assertIn('10. Cross-passage consistency', rubric)
        aspects = read(stage_schema('review', settings))['properties']['reporting_and_statistics']['items']['properties']['aspect']['enum']
        for aspect in ('unit_of_inference', 'scale_and_model', 'batch_and_metadata', 'negative_evidence'):
            self.assertIn(aspect, aspects)
        old = read(stage_schema('review', {'rubric': 'scientific-method-v1.2.0'}))['properties']['reporting_and_statistics']['items']['properties']['aspect']['enum']
        self.assertNotIn('unit_of_inference', old)
        self.assertIn('leave the check out', stage_prompt('crosscheck', settings))

    def test_caption_pattern_accepts_common_journal_styles(self):
        from scientific_review.pdf import CAPTION
        for text in ('Figure 1. Legend', 'Fig. 2: Legend', 'Fig. 3 | Legend', 'Figure S4 \u2014 Legend', 'Fig. 5 \u2013 Legend'):
            self.assertTrue(CAPTION.match(text), text)
        for text in ('Figure 1 shows', 'see Fig. 2 | x', 'Figure legends'):
            self.assertFalse(CAPTION.match(text), text)


if __name__ == '__main__':
    unittest.main()
