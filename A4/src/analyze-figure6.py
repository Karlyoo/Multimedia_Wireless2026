import csv
import hashlib
import json
import os
from pathlib import Path
import tempfile
import warnings

os.environ.setdefault('MPLCONFIGDIR',tempfile.mkdtemp(prefix='a4-figure6-mpl-'))
warnings.filterwarnings('ignore',message='Unable to import Axes3D.*')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'results/figure6'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return np.genfromtxt(path,delimiter=',',names=True)


def db(power):
    return 10*np.log10(np.maximum(power/power.max(),1e-15))


def panels(fig,axes,h,g,dt_us,native_range=False):
    pdp = db(abs(g)**2)
    frequency = db(abs(h)**2)
    first = axes[0].imshow(pdp[:,:10].T,origin='upper',aspect='auto',cmap='viridis',
                           extent=(.5,100.5,9.5*dt_us,-.5*dt_us),vmin=-60,vmax=0,interpolation='nearest')
    axes[0].set(xlim=(.5,100.5),ylim=(.5,0),xlabel='Antenna index',ylabel='Excess delay (μs)',
                title='(a) IDFT-derived power delay profile')
    axes[0].set_yticks([.05,.15,.25,.35,.45])
    second = axes[1].imshow(frequency.T,origin='upper',aspect='auto',cmap='viridis',
                            extent=(.5,100.5,100.5,.5),vmin=float(frequency.min()) if native_range else -20,
                            vmax=0,interpolation='nearest')
    axes[1].set(xlim=(.5,100.5),ylim=(100.5,.5),xlabel='Antenna index',ylabel='Observed tone index',
                title='(b) Power of the transfer function')
    for ax,im in zip(axes,[first,second]):
        fig.colorbar(im,ax=ax,label='Power (dB re global map peak)',fraction=.045,pad=.025)


def main():
    config = json.loads((BASE/'configuration.json').read_text())
    records = json.loads((BASE/'executions.json').read_text())
    assert config['run_ids'] == list(range(1,11)) and len(records) == 11
    assert config['source_sha256'] == sha(ROOT/'src/figure6-channel.cc')
    dt = 1/(config['tones']*config['tone_spacing_hz'])
    delays_us = np.arange(100)*dt*1e6
    summaries = []
    energy_profiles = []
    channel_hashes = []
    max_reconstruction = 0
    max_roundtrip = 0
    max_parseval = 0
    main_h = main_g = None
    for record in records:
        folder = BASE/('repeat-run-01' if record['repeat'] else f'run-{record["run"]:02d}')
        path = folder/'channel.csv'
        assert record['returncode'] == 0
        assert sha(path) == record['channel_sha256']
        assert sha(Path(str(path)+'.clusters.csv')) == record['cluster_sha256']
        rows = load(path)
        assert len(rows) == 10000
        assert np.array_equal(rows['antenna'],np.repeat(np.arange(1,101),100))
        assert np.array_equal(rows['tone'],np.tile(np.arange(1,101),100))
        h = (rows['h_real']+1j*rows['h_imag']).reshape(100,100)
        frequencies = rows['frequency_hz'].reshape(100,100)
        assert np.allclose(frequencies,frequencies[0],rtol=0,atol=0)
        assert np.allclose(np.diff(frequencies[0]),180000,rtol=0,atol=1e-6)
        assert np.isfinite(h).all() and np.sum(abs(h)**2)>0
        clusters = load(Path(str(path)+'.clusters.csv'))
        reconstructed = np.zeros_like(h)
        for c in np.unique(clusters['cluster']):
            part = clusters[clusters['cluster']==c]
            assert np.array_equal(part['antenna'],np.arange(1,101))
            assert np.all(part['delay_s']==part['delay_s'][0]) and part['delay_s'][0]>=0
            coefficient = part['h_real']+1j*part['h_imag']
            reconstructed += coefficient[:,None]*np.exp(-2j*np.pi*frequencies*part['delay_s'][0])
        reconstruction_error = float(np.max(abs(reconstructed-h)))
        assert np.allclose(reconstructed,h,atol=1e-9,rtol=1e-9)
        g = np.fft.ifft(h,axis=1)
        roundtrip = float(np.max(abs(np.fft.fft(g,axis=1)-h)))
        parseval = float(abs(np.sum(abs(g)**2)-np.sum(abs(h)**2)/100)/(np.sum(abs(h)**2)/100))
        assert roundtrip < 1e-10*max(1,float(abs(h).max())) and parseval < 1e-12
        check = json.loads(Path(str(path)+'.check.json').read_text())
        assert check['spectrum_checks']==1 and check['time_s']==0 and check['run']==record['run']
        assert check['max_spectrum_error'] < 1e-8
        max_reconstruction = max(max_reconstruction,reconstruction_error)
        max_roundtrip = max(max_roundtrip,roundtrip)
        max_parseval = max(max_parseval,parseval)
        if record['repeat']:
            assert record['channel_sha256']==records[0]['channel_sha256']
            assert record['cluster_sha256']==records[0]['cluster_sha256']
            continue
        channel_hashes.append(record['channel_sha256'])
        power = abs(h)**2
        delay_power = abs(g)**2
        energy = delay_power.sum(axis=0)/delay_power.sum()
        energy_profiles.append(energy)
        summary = dict(run=record['run'],clusters=check['clusters'],
                       early_100ns_fraction=float(energy[delays_us<=.1+1e-12].sum()),
                       first_three_bins_fraction=float(energy[:3].sum()),
                       through_500ns_fraction=float(energy[delays_us<=.5+1e-12].sum()),
                       frequency_power_roughness=float(abs(np.diff(power,axis=1)).mean()/power.mean()),
                       antenna_index_power_roughness=float(abs(np.diff(power,axis=0)).mean()/power.mean()),
                       frequency_power_dynamic_range_db=float(10*np.log10(power.max()/power.min())),
                       maximum_cluster_excess_delay_ns=float(clusters['delay_s'].max()*1e9),
                       reconstruction_max_error=reconstruction_error,fft_roundtrip_error=roundtrip,
                       parseval_relative_error=parseval)
        summaries.append(summary)
        with (folder/'delay-profile.csv').open('w',newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['delay_bin','delay_us','summed_antenna_power','energy_fraction'])
            writer.writerows(zip(range(100),delays_us,delay_power.sum(axis=0),energy))
        if record['run']==1:
            main_h,main_g = h,g
            with (folder/'cir.csv').open('w',newline='') as stream:
                writer = csv.writer(stream)
                writer.writerow(['antenna','delay_bin','delay_us','cir_real','cir_imag','power'])
                for a in range(100):
                    for n in range(100):
                        writer.writerow([a+1,n,delays_us[n],g[a,n].real,g[a,n].imag,delay_power[a,n]])
    assert len(set(channel_hashes)) == 10
    (BASE/'summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
    with (BASE/'metrics.csv').open('w',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    validation = dict(passed=True,channel_runs=10,repeat_runs=1,spectrum_checks=11,
                      complex_entries_per_snapshot=10000,distinct_channel_hashes=10,
                      repeat_channel_and_cluster_csvs_identical=True,
                      max_direct_reconstruction_error=max_reconstruction,
                      max_fft_roundtrip_error=max_roundtrip,max_parseval_relative_error=max_parseval,
                      native_delay_bin_ns=dt*1e9,unambiguous_delay_us=1/config['tone_spacing_hz']*1e6)
    (BASE/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    fig,axes = plt.subplots(2,1,figsize=(8,7.5))
    panels(fig,axes,main_h,main_g,dt*1e6)
    fig.suptitle('Simulated Figure 6: approximate position A, preselected LOS run 1')
    fig.tight_layout(rect=(0,0,1,.97))
    fig.savefig(BASE/'figure6-simulation.png',dpi=180)
    fig.savefig(BASE/'figure6-simulation.pdf')
    plt.close(fig)
    fig,axes = plt.subplots(2,1,figsize=(8,7.5))
    panels(fig,axes,main_h,main_g,dt*1e6,native_range=True)
    fig.suptitle('Run 1: frequency color scale expanded to its actual data range')
    fig.tight_layout(rect=(0,0,1,.97))
    fig.savefig(BASE/'figure6-native-range.png',dpi=180)
    plt.close(fig)
    fig = plt.figure(figsize=(12,8))
    grid = fig.add_gridspec(2,2,width_ratios=[1,1.15])
    paper = fig.add_subplot(grid[:,0])
    paper.imshow(plt.imread(ROOT/'reference/figure6-source.png'))
    paper.axis('off')
    paper.set_title('Paper Figure 6 (formal IEEE PDF)',fontsize=11)
    axes = [fig.add_subplot(grid[0,1]),fig.add_subplot(grid[1,1])]
    panels(fig,axes,main_h,main_g,dt*1e6)
    fig.suptitle('Qualitative comparison: measured position A vs. statistical LOS surrogate')
    fig.text(.5,.012,'Different explicit dB references; no absolute-power or pixelwise fit is claimed.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.035,1,.96))
    fig.savefig(BASE/'figure6-comparison.png',dpi=180)
    fig.savefig(BASE/'figure6-comparison.pdf')
    plt.close(fig)
    fig,ax = plt.subplots(figsize=(8,4.5))
    profiles = np.array(energy_profiles)
    for profile in profiles:
        ax.plot(delays_us[:10],profile[:10],color='#087f8c',alpha=.2,lw=.8)
    ax.plot(delays_us[:10],profiles[0,:10],color='#087f8c',lw=2,label='Preselected run 1')
    ax.plot(delays_us[:10],profiles.mean(axis=0)[:10],'o--',color='#d07a00',label='Mean over 10 channel runs')
    ax.set(xlim=(0,.5),xlabel='Excess delay (μs)',ylabel='Fraction of total IDFT energy',
           title='Antenna-summed early delay energy (not a published reference curve)')
    ax.legend()
    ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(BASE/'delay-energy-profile.png',dpi=180)
    plt.close(fig)
    print(json.dumps(dict(validation=validation,run1=summaries[0],
                         mean_first_three_bins=float(np.mean([r['first_three_bins_fraction'] for r in summaries]))),indent=2))


if __name__ == '__main__':
    main()
