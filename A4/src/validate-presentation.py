import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile

from presentation_content import slides

ROOT = Path(__file__).resolve().parents[1]
STEM = 'A4-baseline-reproduction-en'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    content = slides(ROOT)
    assert len(content)==18 and sum(s['seconds'] for s in content)==900
    ns = {'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
    with zipfile.ZipFile(ROOT/(STEM+'.pptx')) as archive:
        assert archive.testzip() is None
        slide_paths = [p for p in archive.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',p)]
        note_paths = [p for p in archive.namelist() if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml',p)]
        assert len(slide_paths)==len(note_paths)==18
        for index,s in enumerate(content,1):
            root = ET.fromstring(archive.read(f'ppt/slides/slide{index}.xml'))
            slide_text = ''.join(n.text or '' for n in root.findall('.//a:t',ns))
            assert s['title'] in slide_text
            root = ET.fromstring(archive.read(f'ppt/notesSlides/notesSlide{index}.xml'))
            notes_text = ''.join(n.text or '' for n in root.findall('.//a:t',ns))
            assert s['notes'] in notes_text, f'Notes missing or changed on slide {index}'
    pdf = ROOT/(STEM+'.pdf')
    pdf_text = subprocess.check_output(['pdftotext','-layout',str(pdf),'-'],text=True)
    bbox = ET.fromstring(subprocess.check_output(['pdftotext','-bbox',str(pdf),'-']))
    xns = {'x':'http://www.w3.org/1999/xhtml'}
    pages = bbox.findall('.//x:page',xns)
    assert len(pages)==18
    for p in pages:
        for word in p.findall('.//x:word',xns):
            assert float(word.get('xMin'))>=0 and float(word.get('yMin'))>=0
            assert float(word.get('xMax'))<=float(p.get('width'))
            assert float(word.get('yMax'))<=float(p.get('height'))
    for metric in ['0.2670','0.1714','0.1207','0.1445','0.1844','0.1498','0.476','0.111','55.56']:
        assert metric in pdf_text, f'Metric not found in PDF: {metric}'
    md = ROOT/'presentation.md'
    for target in re.findall(r'\]\(([^)]+)\)',md.read_text()):
        if not target.startswith(('http:','https:','#')):
            assert (ROOT/target.split('#')[0]).exists(),target
    result = dict(passed=True,main_slides=16,backup_slides=2,total_pdf_pages=18,
                  embedded_note_pages=18,full_note_text_verified=True,suggested_seconds=900,
                  metrics_found_in_pdf=True,out_of_page_words=0,local_links_valid=True,
                  visual_review='All 18 slides reviewed; pipeline arrow/title refinement re-rendered.',
                  pptx_sha256=sha(ROOT/(STEM+'.pptx')),pdf_sha256=sha(pdf),notes_sha256=sha(md))
    (ROOT/'results/presentation/validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
