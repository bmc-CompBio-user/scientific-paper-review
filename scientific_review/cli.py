import argparse
import json
from pathlib import Path
import sys
from .config import load
from .evaluation import evaluate
from .pipeline import execute, render_report
from .provider import identity


def main(argv=None):
    parser = argparse.ArgumentParser(description='Local, auditable scientific-method review with Ollama vision')
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('prepare', 'run'):
        p = sub.add_parser(name)
        p.add_argument('manifest')
        p.add_argument('--run-id', required=True)
        p.add_argument('--runs', default='data/runs')
        p.add_argument('--paper', action='append')
        if name == 'run':
            p.add_argument('--max-page-jobs', type=int)
            p.add_argument('--retry-failed', action='store_true')
    p = sub.add_parser('doctor')
    p.add_argument('manifest')
    p = sub.add_parser('report')
    p.add_argument('run_root')
    p = sub.add_parser('evaluate')
    p.add_argument('annotations')
    p.add_argument('run_root')
    p.add_argument('--output', required=True)
    p.add_argument('--minimum-studies', type=int, default=3)
    args = parser.parse_args(argv)
    try:
        if args.command == 'doctor':
            config = load(args.manifest)
            result = identity(config['settings'])
            print(json.dumps({'papers': len(config['papers']), 'provider': result}, indent=2))
        elif args.command == 'report':
            render_report(Path(args.run_root))
            print(str(Path(args.run_root)/'report.md'))
        elif args.command == 'evaluate':
            result = evaluate(args.annotations, args.run_root, args.output, args.minimum_studies)
            print(json.dumps({'annotations': result['annotation_count'], 'families': result['families']}, indent=2))
        else:
            limit = getattr(args, 'max_page_jobs', None)
            if limit is not None and limit < 1:
                raise ValueError('--max-page-jobs must be positive')
            root, errors = execute(args.manifest, args.run_id, args.runs, prepare=args.command == 'prepare',
                paper_ids=args.paper, max_page_jobs=limit, retry_failed=getattr(args, 'retry_failed', False))
            print(json.dumps({'run': str(root), 'errors': errors}, indent=2))
            return 1 if errors else 0
    except Exception as exc:
        print(f'{type(exc).__name__}: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
