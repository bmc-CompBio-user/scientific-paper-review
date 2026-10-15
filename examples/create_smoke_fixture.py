"""Create local synthetic software-test inputs, never biological evidence."""
from pathlib import Path
import pymupdf
from scientific_review.common import write

root = Path('data/smoke')
root.mkdir(parents=True, exist_ok=True)
output = root/'synthetic.pdf'
if output.exists() or (root/'batch.json').exists():
    raise SystemExit('Fixture already exists; preserve it or choose another working directory')
document = pymupdf.open()
page = document.new_page(width=400, height=500)
page.insert_textbox((30, 30, 370, 230),
    'SYNTHETIC STUDY. Figure 1. Inhibition of X lowers reporter Y.\n'
    'A rescue restores Y. Three independent cultures per group.\n'
    'The authors hypothesize direct regulation; no binding assay is reported.', fontsize=12)
page.draw_rect((70, 300, 130, 430), color=(0, 0, 0), fill=(0.2, 0.4, 0.8))
page.draw_rect((180, 370, 240, 430), color=(0, 0, 0), fill=(0.8, 0.4, 0.2))
page.insert_text((70, 455), 'Control           Inhibited')
page = document.new_page(width=400, height=500)
page.insert_textbox((30, 30, 370, 450),
    'METHOD DETAILS\nCultures were randomly allocated to control, inhibitor, or rescue.\n'
    'Three independent cultures per group, technical triplicates averaged.\n'
    'Reporter fluorescence measured after 24 hours.\n'
    'The rescue uses an inhibitor-resistant X construct.\n'
    'No direct binding or transcription measurement was performed.\n'
    'Synthetic fixture for software testing, not real scientific data.', fontsize=12)
document.save(output)
document.close()
write(root/'batch.json', {'papers': [{'id': 'synthetic', 'exploratory': True, 'independence_group': 'synthetic',
    'documents': [{'id': 'main', 'path': 'synthetic.pdf', 'method_pages': [2]}]}]})
print('Created local synthetic fixture. Run: paper-review run data/smoke/batch.json --run-id synthetic-01')
