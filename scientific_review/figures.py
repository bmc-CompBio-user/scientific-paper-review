"""Which page images belong to which figure number, from the extracted pages."""
import re


def figure_number(text):
    match = re.search(r'\bFig(?:ure)?s?\.?\s*(S?\d+)', text, re.I)
    return ('S' if match.group(1).upper().startswith('S') else 'F') + re.sub(r'\D', '', match.group(1)) if match else None


def figure_pages(sources):
    """{'F1': [page, ...]}: image-only pages named 'Figure N' on the page, or the page before a legend page for figure N."""
    pages = sources['pages']
    result = {}
    def add(key, page):
        if key and page['images'] and page not in result.setdefault(key, []):
            result[key].append(page)
    for index, page in enumerate(pages):
        text = ' '.join(b['text'] for b in page['blocks'])
        small = len(text.strip()) < 450 and bool(page['images'])
        label_here = figure_number(text) if small else None
        if small and label_here:
            add(label_here, page)
            continue
        legends = [figure_number(c['label']) if isinstance(c, dict) else figure_number(str(c)) for c in page.get('caption_candidates', [])]
        legends += [figure_number(b['text']) for b in page['blocks'] if re.match(r'\s*(?:Figure|Fig\.)\s*S?\d+\s*[,.:|]', b['text'])]
        for key in legends:
            if key:
                previous = pages[index - 1] if index else None
                if previous and len(' '.join(b['text'] for b in previous['blocks']).strip()) < 450 and previous['images'] and not figure_number(' '.join(b['text'] for b in previous['blocks'])):
                    add(key, previous)
                else:
                    add(key, page)
    return result
