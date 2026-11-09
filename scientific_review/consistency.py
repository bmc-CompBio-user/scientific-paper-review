"""Deterministic comparison of numbers in different passages of one manuscript.

A difference is reported only when two passages on different pages state the same kind of quantity (sample size, dose, duration, threshold, count of a named entity)
with different values and share several content words around the number. No model is involved; both quotes are slices of the source blocks."""
import re
from .common import PACKAGE

STOP = set('''the and for with that this from were was are has have had its into than then which also both each other these those their there here when where while
using used use after before during under over between within without such been being not but can may could would should will shall per via only more most less
than one two three four five six seven eight nine ten first second third figure fig table panel panels shown show shows showed data results result analysis analyses
compared control controls group groups sample samples cells cell treated untreated were respectively experiment experiments performed obtained'''.split())
KINDS = (
    ('sample_size_or_replicates', 'n', re.compile(r'\b[nN]\s*=\s*(\d+)\b')),
    ('sample_size_or_replicates', 'replicates', re.compile(r'\b(\d+)\s+(?:independent\s+|biological\s+|technical\s+)?(?:replicates?|replicas?|animals|mice|donors|clones|cultures|flies|larvae)\b')),
    ('amount_dose_or_duration', 'amount', re.compile(r'(?<![\w.])(\d+(?:\.\d+)?)\s*(Gy|nM|µM|μM|uM|mM|µg/ml|ug/ml|ng/ml|mg/ml|U/ml|µl|ml|µg|ng|mg)\b')),
    ('amount_dose_or_duration', 'duration', re.compile(r'(?<![\w.])(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|min|minutes?|days?|weeks?)\b')),
    ('threshold_or_cutoff', 'threshold', re.compile(r'\b(FDR|q|P|p|padj|adjusted\s+[pP])(?:[- ]?value)?\s*(?:<|≤|<=|=)\s*(0?\.\d+|\d+(?:\.\d+)?\s*[eE][-−]?\d+)')),
    ('text_vs_legend_or_figure_claim', 'count', re.compile(r'(?<![\w.])(\d{1,3}(?:,\d{3})+|\d{3,})\s+((?:[a-z][a-z-]+\s+){0,2}(?:genes|sites|peaks|DEGs|regions|loci|nucleosomes|patients|donors|proteins|sequences|reads|cells))\b', re.I)),
    ('text_vs_legend_or_figure_claim', 'count', re.compile(r'(?:genes|sites|peaks|DEGs|regions|loci|nucleosomes|patients|donors|proteins|sequences|reads|cells)\s*\(\s*(\d{1,3}(?:,\d{3})+|\d{3,})\s*\)', re.I)),
)
LIST_WORDS = re.compile(r'\b(respectively|versus|vs\.?|compared (?:to|with)|whereas|in contrast|and \d)\b', re.I)


def words(text):
    return {w for w in re.findall(r'[A-Za-z][A-Za-z0-9\-]{2,}', text.lower()) if w not in STOP}


def sentence_around(text, start, end):
    left = max(text.rfind('. ', 0, start), text.rfind('\n', 0, start))
    right_candidates = [i for i in (text.find('. ', end), text.find('\n', end)) if i >= 0]
    right = min(right_candidates) if right_candidates else len(text)
    return text[left + 2 if left >= 0 else 0: right + 1].strip()


def facts(page):
    found = []
    for block in page['blocks']:
        text = block['text']
        for category, kind, pattern in KINDS:
            for match in pattern.finditer(text):
                value_text = match.group(1).replace(',', '')
                label = match.group(2).lower() if kind in ('amount', 'duration', 'count', 'threshold') and match.lastindex >= 2 else ''
                try:
                    value = float(re.sub(r'\s', '', value_text))
                except ValueError:
                    continue
                sentence = sentence_around(text, match.start(), match.end())
                window = text[max(0, match.start() - 90): match.end() + 90]
                found.append(dict(category=category, kind=kind, label=label.replace('hrs', 'h').replace('hr', 'h') if kind == 'duration' else label, value=value, raw=match.group(0),
                                  block=block['id'], page=page['id'], role=page['role_hint'], sentence=sentence[:300], context=words(window) - words(match.group(0)), listy=bool(LIST_WORDS.search(sentence))))
    return found


def compare(sources, min_shared=3):
    all_facts = []
    for page in sources['pages']:
        if page['role_hint'] in ('references_candidate', 'resources'):
            continue
        all_facts += facts(page)
    checks, seen = [], set()
    for i, a in enumerate(all_facts):
        for b in all_facts[i + 1:]:
            if a['kind'] not in ('count', 'threshold') or a['kind'] != b['kind'] or a['label'] != b['label'] or a['value'] == b['value'] or a['page'] == b['page']:
                continue
            if a['listy'] or b['listy']:
                continue
            low, high = sorted((a['value'], b['value']))
            if a['kind'] == 'count' and (low < 100 or high / low > 1.7):
                continue  # counts of very different size are not two statements of one number
            if a['kind'] == 'threshold' and high / low > 25:
                continue
            shared = sorted(a['context'] & b['context'])
            if len(shared) < min_shared:
                continue
            key = (a['block'], b['block'], a['kind'], a['value'], b['value'])
            if key in seen:
                continue
            seen.add(key)
            checks.append(dict(id=f'num_{len(checks) + 1}', category=a['category'], tier='code', topic=f"{a['kind']} {a['label']}".strip() + ': ' + ', '.join(shared[:6]), relation='numeric_difference',
                               passages=[dict(source=a['block'], quote=a['sentence']), dict(source=b['block'], quote=b['sentence'])],
                               explanation=f"{a['raw']} ({a['block']}) versus {b['raw']} ({b['block']}): the two passages share the context words {', '.join(shared[:6])} and state different values of the same kind of quantity. They may describe different groups or experiments; check the text.",
                               consequence='', declared_consistent=False, method='code'))
    return checks


def numeric_crosscheck(sources, verify):
    """Result in the format of the model cross-check, with quote checks done by the same code path."""
    checks = compare(sources)
    checks = [{**c, 'passages': [{**p, 'quote_verified': verify(p)} for p in c['passages']]} for c in checks]
    return {'scope': 'numeric differences between passages, found by code', 'checks': checks, 'not_checked': ['claims that depend on figure panels', 'differences in wording', 'passages in documents that were not supplied'], 'method': 'code'}


def fact_values(text):
    """(category, kind, label, value) of every quantity in a quote."""
    out = []
    for category, kind, pattern in KINDS:
        for match in pattern.finditer(text):
            try:
                value = float(re.sub(r'\s', '', match.group(1).replace(',', '')))
            except ValueError:
                continue
            label = match.group(2).lower() if match.lastindex and match.lastindex >= 2 else ''
            out.append((category, kind, label, value))
    return out


def numeric_gate(check):
    """A model-proposed difference is kept only if its two quotes state the same kind of quantity with different values."""
    quotes = [p['quote'] for p in check['passages']]
    if len(quotes) < 2:
        return False
    first, second = fact_values(quotes[0]), fact_values(quotes[1])
    for ca, ka, la, va in first:
        for cb, kb, lb, vb in second:
            if ka == kb and la == lb and va != vb:
                return True
    return False


def gate_crosscheck(result):
    """Drop model cross-check items that are not numeric differences; relabel the rest. The result keeps its own list of what was dropped."""
    kept, dropped = [], 0
    for check in result['checks']:
        if numeric_gate(check):
            kept.append({**check, 'relation': 'numeric_difference', 'tier': 'model-proposed'})
        else:
            dropped += 1
    return {**result, 'checks': kept, 'dropped_non_numeric': dropped}
