import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf',type=Path)
    args = parser.parse_args()
    command = ['pdftoppm','-f','7','-l','7','-scale-to','1800','-x','90','-y','140',
               '-W','540','-H','540','-png','-singlefile',str(args.pdf),str(ROOT/'reference/figure6-source')]
    subprocess.run(command,check=True)
    provenance = dict(doi='10.1109/TMLCN.2023.3334712',source='User-provided formal IEEE PDF',
                      source_filename=args.pdf.name,pdf_sha256=hashlib.sha256(args.pdf.read_bytes()).hexdigest(),
                      pdf_page=7,printed_page=25,figure=6,extract_command=command,
                      position_A_source=dict(pdf_page=6,printed_page=24,figure=5,
                          image_object='377 0',native_image_size_px=[857,605],
                          scan_bounds_px=dict(left=242,right=722,top=122,bottom=483),
                          approximate_A_center_px=[481,269],region_size_m=[4.2,2.5],
                          within_region_estimate_m=[(481-242)/(722-242)*4.2,(269-122)/(483-122)*2.5],
                          assumed_region_origin_m=[1.1,-.6],rounded_simulated_A_m=[3.19,.42,1.73],
                          note='Manual schematic proportional estimate, not a surveyed point or precision claim. Face-plane and array-center assumptions inherited from the approved geometry study.'),
                      paper_color_reference='Relative power in dB; full measurement tensor/RF calibration unavailable. No absolute dB matching inferred.',
                      comparison='Side-by-side image; no numerical heatmap digitization or pixelwise matching.',
                      accessed_date='2026-11-23')
    (ROOT/'reference/figure6-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print('Formal Figure 6 crop and schematic point-A provenance saved.')


if __name__ == '__main__':
    main()
