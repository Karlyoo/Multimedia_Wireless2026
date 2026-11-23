import importlib.util
import json
from pathlib import Path
import re
import zipfile
from xml.sax.saxutils import escape

from PIL import Image
from presentation_content import slides

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'results/presentation'
STEM = 'A4-baseline-reproduction-en'


def make_assets():
    import os
    import tempfile
    import warnings
    os.environ.setdefault('MPLCONFIGDIR',tempfile.mkdtemp(prefix='a4-slides-mpl-'))
    warnings.filterwarnings('ignore',message='Unable to import Axes3D.*')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.patches import Rectangle
    ASSETS.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.size':16,'axes.titlesize':16,'axes.labelsize':17,'legend.fontsize':11})
    def load(path):
        return np.genfromtxt(ROOT/path,delimiter=',',names=True)
    ref = load('reference/figure7.csv')
    x = load('results/los-aggregate.csv')['distance_lambda']
    def new():
        fig,ax = plt.subplots(figsize=(9,5),dpi=160)
        ax.plot(ref['distance_lambda'],ref['abs_rho'],'o--',color='#3d3bd1',lw=2,ms=4,label='Paper Fig. 7 (post-print)')
        ax.set(xlim=(0,2.1875),ylim=(.2,1.01),xlabel='Separation / wavelength',ylabel='Correlation magnitude')
        ax.set_xticks(np.arange(0,2.01,.5))
        ax.grid(alpha=.22)
        return fig,ax
    def save(fig,ax,name):
        ax.legend(loc='best',framealpha=.9)
        fig.tight_layout()
        fig.savefig(ASSETS/(name+'.png'))
        plt.close(fig)
    fig,ax = new()
    d = load('results/full/los/run-01/correlation.csv')
    ax.plot(x,d['abs_rho'],color='#087f8c',lw=3,label='LOS run 1, 42 s')
    save(fig,ax,'single')
    fig,ax = new()
    d = load('results/los-aggregate.csv')
    ax.fill_between(x,d['min_abs_rho'],d['max_abs_rho'],color='#087f8c',alpha=.15,label='Run min–max (not CI)')
    ax.plot(x,d['mean_abs_rho'],color='#087f8c',lw=3,label='LOS mean, n=10')
    save(fig,ax,'ensemble')
    fig,ax = new()
    for label,color in [('noiseless','#087f8c'),('1','#cc4b30'),('6','#d39400'),('11','#397d40')]:
        d = load(f'results/noise/aggregate-{label}.csv')
        ax.plot(x,d['mean_abs_rho'],color=color,lw=2.5,label='Noiseless' if label=='noiseless' else label+' dB')
    save(fig,ax,'noise')
    fig,ax = new()
    ax.set_ylim(0,1.02)
    for label,color in [('control-x','#c17a00'),('control-y','#a73773')]:
        d = load(f'results/geometry/aggregate-{label}.csv')
        ax.fill_between(x,d['min_abs_rho'],d['max_abs_rho'],color=color,alpha=.09)
        ax.plot(x,d['mean_abs_rho'],color=color,lw=3,label=label+' mean, n=10')
    save(fig,ax,'direction')
    fig,ax = plt.subplots(figsize=(8,5),dpi=160)
    ax.add_patch(Rectangle((1.1,-.6),4.2,2.5,facecolor='#edf3f7',edgecolor='#777777'))
    ax.plot([0,0],[-.6,.6],color='#203047',lw=10)
    ax.plot(0,0,'ks',ms=6)
    ax.plot(1.1,-.6,'ko',ms=6)
    for end,color in [((5.3,-.6),'#087f8c'),((1.1,1.9),'#a73773')]:
        ax.annotate('',xy=end,xytext=(1.1,-.6),arrowprops={'arrowstyle':'->','lw':3,'color':color})
    ax.text(2.6,-.85,'+x: 4.2 m',color='#087f8c')
    ax.text(1.3,1.4,'+y control: 2.5 m',color='#a73773',fontsize=12)
    ax.text(2.6,1.7,'4.2 × 2.5 m scan region',fontsize=13)
    ax.text(.05,-.9,'Assumed 1.1 m gap',fontsize=12)
    ax.text(-.2,.9,'BS',fontsize=14)
    ax.set(xlim=(-.4,5.6),ylim=(2.2,-1.2),xlabel='x (m)',ylabel='y (m)',aspect='equal')
    ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(ASSETS/'path.png')
    plt.close(fig)
    raw = load('results/figure6/run-01/channel.csv')
    h = (raw['h_real']+1j*raw['h_imag']).reshape(100,100)
    g = np.fft.ifft(h,axis=1)
    def db(p):
        return 10*np.log10(np.maximum(p/p.max(),1e-15))
    fig = plt.figure(figsize=(12,5.5),dpi=180)
    grid = fig.add_gridspec(2,2,width_ratios=[1,1.25])
    ax = fig.add_subplot(grid[:,0])
    ax.imshow(plt.imread(ROOT/'reference/figure6-source.png'))
    ax.axis('off')
    ax.set_title('Paper: formal PDF',fontsize=15)
    a,b = fig.add_subplot(grid[0,1]),fig.add_subplot(grid[1,1])
    im = a.imshow(db(abs(g)**2)[:,:10].T,aspect='auto',origin='upper',cmap='viridis',
                  extent=(.5,100.5,9.5/18,-.5/18),vmin=-60,vmax=0)
    a.set(xlim=(.5,100.5),ylim=(.5,0),ylabel='Excess delay (μs)',title='Simulated PDP: run 1')
    im2 = b.imshow(db(abs(h)**2).T,aspect='auto',origin='upper',cmap='viridis',
                   extent=(.5,100.5,100.5,.5),vmin=-20,vmax=0)
    b.set(xlabel='Antenna index',ylabel='Tone index',title='Simulated transfer power')
    a.tick_params(labelsize=12)
    b.tick_params(labelsize=12)
    for axis,im in [(a,im),(b,im2)]:
        cb = fig.colorbar(im,ax=axis,fraction=.035,pad=.03)
        cb.ax.tick_params(labelsize=11)
        cb.set_label('dB re map peak',fontsize=12)
    fig.tight_layout()
    fig.savefig(ASSETS/'figure6.png')
    plt.close(fig)


def text_xml(value,style='Body'):
    return ''.join(f'<text:p text:style-name="{style}">{escape(line) or " "}</text:p>' for line in value.split('\n'))


def frame(x,y,w,h,value,style='Body'):
    return f'<draw:frame draw:style-name="Plain" svg:x="{x}cm" svg:y="{y}cm" svg:width="{w}cm" svg:height="{h}cm"><draw:text-box>{text_xml(value,style)}</draw:text-box></draw:frame>'


def rect(x,y,w,h,style):
    return f'<draw:rect draw:style-name="{style}" svg:x="{x}cm" svg:y="{y}cm" svg:width="{w}cm" svg:height="{h}cm"/>'


def picture(path,x,y,w,h):
    with Image.open(path) as im:
        ratio = im.width/im.height
    if w/h > ratio:
        actual_h,actual_w = h,h*ratio
    else:
        actual_w,actual_h = w,w/ratio
    x,y = x+(w-actual_w)/2,y+(h-actual_h)/2
    return f'<draw:frame draw:style-name="Plain" svg:x="{x}cm" svg:y="{y}cm" svg:width="{actual_w}cm" svg:height="{actual_h}cm"><draw:image xlink:href="Pictures/{path.name}" xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad"/></draw:frame>'


def main():
    make_assets()
    content = slides(ROOT)
    assert len(content)==18 and sum(s['seconds'] for s in content)==900
    assert all(s['seconds']>0 for s in content[:16]) and all(s['seconds']==0 for s in content[16:])
    ns = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
          'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
          'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
          'xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" '
          'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" '
          'xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" '
          'xmlns:presentation="urn:oasis:names:tc:opendocument:xmlns:presentation:1.0" '
          'xmlns:xlink="http://www.w3.org/1999/xlink"')
    styles = []
    for name,size,color,weight in [('Title',29,'#142d4e','bold'),('Sub',14,'#087f8c','normal'),
                                  ('Body',21,'#203047','normal'),('Side',17,'#203047','normal'),
                                  ('Cell',18,'#203047','normal'),('Card',17,'#203047','normal'),
                                  ('CardTitle',18,'#087f8c','bold'),('Take',17,'#ffffff','bold'),
                                  ('Foot',9,'#607080','normal'),('Note',12,'#203047','normal')]:
        styles.append(f'<style:style style:name="{name}" style:family="paragraph"><style:paragraph-properties fo:margin-bottom="0.22cm" fo:line-height="120%"/><style:text-properties fo:font-family="Liberation Sans" fo:font-size="{size}pt" fo:color="{color}" fo:font-weight="{weight}"/></style:style>')
    for name,fill,color in [('Plain','none','#ffffff'),('Navy','solid','#142d4e'),('Teal','solid','#087f8c'),('Pale','solid','#edf3f7'),('White','solid','#ffffff')]:
        styles.append(f'<style:style style:name="{name}" style:family="graphic"><style:graphic-properties draw:stroke="none" draw:fill="{fill}" draw:fill-color="{color}" fo:padding="0cm"/></style:style>')
    styles.append('<style:style style:name="Page" style:family="drawing-page"><style:drawing-page-properties draw:fill="solid" draw:fill-color="#ffffff"/></style:style>')
    pages = []
    md = ['# A4 — English Presentation and Speaker Notes','','16 main slides: suggested timing 15:00, excluding Q&A. Two backup slides are untimed. Timing is a rehearsal target, not a measured recording.','','Sources: [main study](study_note.md), [noise](noise_study.md), [geometry](geometry_study.md), [small tests](sensitivity_study.md), [Figure 6](figure6_study.md).','','Speaker notes are embedded in the PowerPoint. Graphs are redrawn from existing CSVs for presentation legibility; no new simulations are run.','']
    elapsed = 0
    for index,s in enumerate(content,1):
        body = rect(0,0,33.867,.22,'Teal') + frame(1.2,.65,31.4,1.4,s['title'],'Title')
        body += frame(1.25,2.15,31,.75,s['subtitle'],'Sub')
        if 'image' in s:
            path = ASSETS/(s['image']+'.png')
            if s.get('wide'):
                body += picture(path,1.15,3.05,31.5,12.3)
            else:
                body += picture(path,.8,3.1,23.0,12.0)
                for i,line in enumerate(s['sidebar']):
                    body += rect(24.2,3.8+i*2.65,8.4,2.35,'Pale')
                    body += frame(24.55,4.05+i*2.65,7.65,1.95,line,'Side')
        elif 'table' in s:
            widths = [14,8,9.3]
            for row_index,row in enumerate(s['table']):
                y = 3.5+row_index*1.8
                body += rect(1.25,y,31.3,1.65,'Pale' if row_index%2==0 else 'White')
                x = 1.6
                for j,cell in enumerate(row):
                    body += frame(x,y+.25,widths[j]-.5,1.3,cell,'Cell')
                    x += widths[j]
        elif 'rows' in s:
            height = min(2.15,11.8/len(s['rows']))
            for i,(left,right) in enumerate(s['rows']):
                y = 3.45+i*height
                body += rect(1.25,y,31.3,height-.12,'Pale' if i%2==0 else 'White')
                body += frame(1.6,y+.22,8.3,height-.2,left,'Cell')
                body += frame(10.35,y+.22,21.7,height-.2,right,'Cell')
        elif 'pipeline' in s:
            for i,(title,value) in enumerate(s['pipeline']):
                x = 1.25+i*8.0
                body += rect(x,3.8,7.25,6.4,'Pale')
                body += frame(x+.3,4.25,6.65,1.1,title,'CardTitle')
                body += frame(x+.3,5.8,6.65,3.9,value,'Card')
                if i<3:
                    body += frame(x+7.25,6.5,.75,1,'→','CardTitle')
            if 'formula' in s:
                body += frame(1.55,11.0,30.5,1.15,s['formula'],'Side')
            y = 12.6 if 'formula' in s else 11.0
            for i,line in enumerate(s['bullets']):
                body += frame(1.5,y+i*1.8,30.5,1.55,line,'Side')
        else:
            for i,line in enumerate(s['bullets']):
                body += frame(1.5,3.9+i*2.35,30.5,1.95,'•  '+line,'Body')
        body += rect(0,16.05,33.867,1.65,'Navy')
        body += frame(1.2,16.35,31.3,1.15,s['takeaway'],'Take')
        body += frame(1.2,18.05,29.8,.65,s['source'],'Foot')
        body += frame(31.4,18.05,2,.65,f'{index:02d} / 18','Foot')
        timing = f'Suggested time: {s["seconds"]} seconds' if s['seconds'] else 'Untimed backup slide'
        body += '<presentation:notes><draw:frame presentation:class="notes" svg:x="1cm" svg:y="1cm" svg:width="26cm" svg:height="16cm"><draw:text-box>'+text_xml(timing+'\n'+s['notes'],'Note')+'</draw:text-box></draw:frame></presentation:notes>'
        pages.append(f'<draw:page draw:name="Slide{index}" draw:style-name="Page" draw:master-page-name="Default">{body}</draw:page>')
        start = f'{elapsed//60}:{elapsed%60:02d}'
        elapsed += s['seconds']
        end = f'{elapsed//60}:{elapsed%60:02d}'
        md.extend([f'## {index}. {s["title"]} ({start}–{end})' if s['seconds'] else f'## {index}. {s["title"]} (backup)', '',s['subtitle'],''])
        for line in s.get('bullets',s.get('sidebar',[])):
            md.append('- '+line)
        for row in s.get('rows',s.get('table',[])):
            md.append('- '+' | '.join(row))
        for title,value in s.get('pipeline',[]):
            md.append('- '+title+': '+value.replace('\n','; '))
        if s.get('image'):
            md.extend(['',f'![Slide graphic](results/presentation/{s["image"]}.png)'])
        md.extend(['','> '+s['takeaway'],'','Speaker notes:','',s['notes'],'','Source: '+s['source'],''])
    document = f'<?xml version="1.0" encoding="UTF-8"?><office:document-content {ns} office:version="1.2"><office:automatic-styles>{"".join(styles)}</office:automatic-styles><office:body><office:presentation>{"".join(pages)}</office:presentation></office:body></office:document-content>'
    style_doc = f'<?xml version="1.0" encoding="UTF-8"?><office:document-styles {ns} office:version="1.2"><office:styles/><office:automatic-styles><style:page-layout style:name="Layout"><style:page-layout-properties fo:page-width="33.867cm" fo:page-height="19.05cm" style:print-orientation="landscape"/></style:page-layout></office:automatic-styles><office:master-styles><style:master-page style:name="Default" style:page-layout-name="Layout"/></office:master-styles></office:document-styles>'
    pictures = sorted(ASSETS.glob('*.png'))
    entries = [('content.xml','text/xml'),('styles.xml','text/xml')]+[(f'Pictures/{p.name}','image/png') for p in pictures]
    manifest = '<?xml version="1.0"?><manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2"><manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.presentation"/>'+''.join(f'<manifest:file-entry manifest:full-path="{name}" manifest:media-type="{mime}"/>' for name,mime in entries)+'</manifest:manifest>'
    with zipfile.ZipFile(ROOT/(STEM+'.odp'),'w') as z:
        z.writestr('mimetype','application/vnd.oasis.opendocument.presentation',compress_type=zipfile.ZIP_STORED)
        z.writestr('content.xml',document)
        z.writestr('styles.xml',style_doc)
        z.writestr('META-INF/manifest.xml',manifest)
        for p in pictures:
            z.write(p,'Pictures/'+p.name)
    md.extend(['## Rebuild and Export','','```bash','python3 A4/src/build-presentation.py',f'libreoffice -env:UserInstallation=file:///tmp/a4-slides-lo --headless --convert-to pptx --outdir A4 A4/{STEM}.odp',f'libreoffice -env:UserInstallation=file:///tmp/a4-slides-lo --headless --convert-to pdf --outdir A4 A4/{STEM}.odp','```','','Simulation and analysis commands: [src/README.md](src/README.md). Rebuilding these slides does not rerun simulations.',''])
    (ROOT/'presentation.md').write_text('\n'.join(md),encoding='utf-8')
    metadata = dict(main_slides=16,backup_slides=2,total_slides=18,suggested_seconds=elapsed,
                    main_notes_word_count=sum(len(re.findall(r"\b[\w’'-]+\b",s['notes'])) for s in content[:16]),
                    timings=[dict(slide=i+1,title=s['title'],seconds=s['seconds']) for i,s in enumerate(content)])
    (ASSETS/'timing.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata,indent=2))


if __name__ == '__main__':
    main()
