"""Scope of absence findings: what was searched, and which absence claims may be answered by figure panels that the text stages do not read."""
import re

ABSENCE = re.compile(r"\b(not (?:explicitly |clearly |always )?(?:stated|specified|mentioned|reported|described|defined|provided|given|indicated|shown|disclosed|listed|known)"
                     r"|no (?:mention|information|indication|statement|description|details?|explicit)"
                     r"|(?:does|do|did) not (?:state|specify|mention|report|describe|define|provide|indicate|say|list|clarify|explain)"
                     r"|lack(?:s|ing)?|absent|missing|omit(?:s|ted)?|without (?:stating|specifying|reporting)|unclear|cannot be (?:determined|verified|assessed))\b", re.I)
# Things that usually sit in axis labels, panel annotations, graphs or scale bars rather than in running text or legends.
FIGURE_BORNE = (
    ('time points', re.compile(r'\b(?:time[- ]?points?|timepoints|sampling times?|harvest(?:ed|ing)? times?|exact times?|which time|specific (?:days|hours|times)|days? post|hours? post|which days|number of days|the days)\b', re.I)),
    ('doses or concentrations', re.compile(r'\b(?:concentrations?|doses?|dosage|amounts? of (?:plasmid|siRNA|drug|DNA|protein)|titration|dose[- ]response)\b', re.I)),
    ('data points or error bars shown', re.compile(r'\b(?:individual (?:data )?points|data points (?:are |were )?(?:shown|plotted|displayed)|error bars? (?:are |is )?(?:shown|plotted|present|displayed))\b', re.I)),
    ('scale or axis', re.compile(r'\b(?:scale bars?|axis|axes|y-axis|x-axis|axis labels?|log(?:arithmic)? scale|magnification|unit(?:s)? of the)\b', re.I)),
    ('panel annotations', re.compile(r'\b(?:annotat(?:ed|ions?)|labell?ed|labels?|marker lanes?|molecular weight|loading control shown|lane labels?|legend of the (?:panel|graph)|channel)\b', re.I)),
)


def absence_claim(text):
    return bool(ABSENCE.search(text))


def figure_borne(text):
    return [name for name, pattern in FIGURE_BORNE if pattern.search(text)]


def scope_flag(item):
    """'figure:<what>' when a sentence of the finding asserts that something is not stated and that something typically sits in figure panels."""
    text = ' '.join(str(item.get(k, '')) for k in ('finding', 'topic'))
    tags = []
    for match in ABSENCE.finditer(text):
        window = text[max(0, match.start() - 110): match.end() + 140]
        for tag in figure_borne(window):
            if tag not in tags:
                tags.append(tag)
    return 'figure:' + ', '.join(tags) if tags else ''


def coverage_statement(sources):
    documents = sorted({p['document'] for p in sources['pages']})
    pages = len(sources['pages'])
    text_pages = sum(1 for p in sources['pages'] if p['blocks'])
    return (f"Searched: the extracted text of {pages} page(s) of {len(documents)} supplied document(s) ({', '.join(documents)}); "
            f"not searched: files that were not supplied (for example supplementary files and source data), and the content of figure panels (axis labels, annotations, scale bars, blots), "
            f"which the text stages do not read. 'Not stated' means not stated in this supplied text.")
