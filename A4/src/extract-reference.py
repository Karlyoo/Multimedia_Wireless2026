import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://lucris.lub.lu.se/ws/portalfiles/portal/165039395/TMLCN.pdf'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf', type=Path)
    args = parser.parse_args()
    folder = ROOT / 'reference'
    folder.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='a4-reference-'))
    svg = temp / 'page.svg'
    subprocess.run(['pdftocairo', '-f', '9', '-l', '9', '-svg', str(args.pdf), str(svg)], check=True)
    paths = [node for node in ET.parse(svg).iter()
             if 'stroke:rgb(0%,0%,100%)' in node.get('style', '')]
    assert len(paths) == 1, 'Source differs: inspect figure rather than guessing a path'
    path = paths[0]
    numbers = [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', path.attrib['d'])]
    assert len(numbers) == 66
    coordinates = list(zip(numbers[::2], numbers[1::2]))
    x0, x2 = 309.620661, 1973.025382
    y02, y1 = 177.870077, 1453.897954
    points = [(2 * (x - x0) / (x2 - x0), .2 + .8 * (y - y02) / (y1 - y02))
              for x, y in coordinates]
    assert abs(points[0][0]) < 1e-6 and abs(points[0][1] - 1) < 1e-6
    assert abs(points[-1][0] - 2) < 1e-6
    with (folder / 'figure7.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['distance_lambda', 'abs_rho'])
        writer.writerows(points)
    metadata = dict(source_url=URL, doi='10.1109/TMLCN.2023.3334712',
                    source_version='University-hosted accepted manuscript / post-print',
                    pdf_sha256=hashlib.sha256(args.pdf.read_bytes()).hexdigest(),
                    pdf_page=9, printed_page=7, figure=7, point_count=len(points),
                    method='Extract blue dashed polyline vertices from pdftocairo SVG; linear tick calibration.',
                    curve_path=path.attrib, calibration=dict(x0=x0, x2=x2, y02=y02, y1=y1),
                    original_plot_xlim=[0, 2 * (2128.989554-x0)/(x2-x0)],
                    original_plot_ylim=[.2, 1],
                    precision_note='Vector-path recovery, not experimental raw data. Conservative coordinate-reporting tolerance: 0.0001 on each axis; not a statistical confidence interval.',
                    accessed_local_date='2026-11-21',
                    figure_note='Figure numbering and equation checked against published-author full text. Numerical extraction uses the university post-print; publisher-version numerical identity was not independently established.')
    (folder / 'provenance.json').write_text(json.dumps(metadata, indent=2) + '\n')
    subprocess.run(['pdftoppm', '-f', '9', '-l', '9', '-scale-to', '1600',
                    '-x', '128', '-y', '736', '-W', '490', '-H', '400', '-png', '-singlefile',
                    str(args.pdf), str(folder / 'figure7-source')], check=True)
    print(f'Extracted {len(points)} reference vertices; last point={points[-1]}')


if __name__ == '__main__':
    main()
