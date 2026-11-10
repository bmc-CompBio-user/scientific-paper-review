"""Group per-experiment concerns that repeat one issue across experiments, by shared phrases rather than by a model."""
import re
from collections import defaultdict

FILLER = set('''the a an of in for and or to is are was were be been being that this these those which with as by on at it its not no does do did text states state stated
specify specified explicitly explicit whether if but however also than then there their they can could may might would should will shall from into over under between within
without such any all each both more most less only very just so thus therefore yet while when where what how why who whom whose have has had having per via'''.split())
GENERIC = set('''text figure panel panels data result results analysis experiment experiments study authors reported report reports describe described describes provided provide
given give shown show shows included include statement information details detail section methods method legend legends main supplied'''.split())


def tokens(text):
    words = [w.strip("'-") for w in re.findall(r"[a-z\u00b5][a-z0-9\-\u00b5']*|\d+(?:\.\d+)?", text.lower())]
    return ['#' if re.fullmatch(r'\d+(?:\.\d+)?', w) else w for w in words if w and w not in FILLER]


def ngrams(text, sizes=(3, 4)):
    words = tokens(text)
    found = set()
    for n in sizes:
        for i in range(len(words) - n + 1):
            gram = tuple(words[i:i + n])
            informative = [w for w in gram if w != '#' and w not in GENERIC]
            if len(informative) >= 2 and gram[0] != '#' and gram[-1] != '#':
                found.add(gram)
    return found


def recurring_issues(checks, min_support=3):
    """[{theme, labels, aspects, items}] for phrases that recur in concerns of at least min_support different experiments; each concern joins at most one group."""
    concerns = []
    for result in checks:
        for item in result['items']:
            if item['status'] == 'concern' and (item.get('figure_check') or {}).get('answer') != 'visible':
                concerns.append({'experiment_id': result['experiment_id'], 'label': result.get('label', ''), 'item': item, 'grams': ngrams(item['finding'])})
    remaining = list(range(len(concerns)))
    groups = []
    while True:
        support = defaultdict(set)
        for index in remaining:
            for gram in concerns[index]['grams']:
                support[gram].add(concerns[index]['experiment_id'])
        candidates = [(len(ids), len(gram), gram) for gram, ids in support.items() if len(ids) >= min_support]
        if not candidates:
            break
        best = max(candidates)
        gram = best[2]
        members = [i for i in remaining if gram in concerns[i]['grams']]
        groups.append({'theme': ' '.join(gram), 'labels': sorted({concerns[i]['label'] for i in members}), 'aspects': sorted({concerns[i]['item']['item'] for i in members}),
                       'items': [{'experiment_id': concerns[i]['experiment_id'], 'label': concerns[i]['label'], **{k: concerns[i]['item'][k] for k in ('item', 'finding', 'evidence', 'figure_check') if k in concerns[i]['item']}} for i in members]})
        remaining = [i for i in remaining if i not in members]
    rest = [{'experiment_id': concerns[i]['experiment_id'], 'label': concerns[i]['label'], 'item': concerns[i]['item']} for i in remaining]
    return groups, rest


def representative(group):
    """The group's concern that contains the most words of the theme phrase; shorter wins a tie, a verified quote breaks a further tie."""
    theme = set(group['theme'].split()) - {'#'}
    def key(item):
        words = set(tokens(item['finding']))
        verified = any(q.get('quote_verified') for q in item.get('evidence', []))
        return (-len(theme & words), 0 if verified else 1, len(item['finding']))
    return min(group['items'], key=key)
