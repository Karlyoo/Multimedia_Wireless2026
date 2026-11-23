import csv
import hashlib
import json
import os
from pathlib import Path
import tempfile
import warnings

os.environ.setdefault('MPLCONFIGDIR', tempfile.mkdtemp(prefix='a4-geometry-mpl-'))
warnings.filterwarnings('ignore', message='Unable to import Axes3D.*')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/geometry'
NAMES = ['paper-x-full', 'control-x', 'control-y']
COLORS = {'baseline':'#555555', 'paper-x-full':'#087f8c', 'control-x':'#d38700', 'control-y':'#a33a71'}


def load(path):
    return np.genfromtxt(path, delimiter=',', names=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    configuration = json.loads((BASE / 'configuration.json').read_text())
    records = json.loads((BASE / 'executions.json').read_text())
    assert len(records) == 30
    assert configuration['source_sha256'] == sha(ROOT / 'src/geometry-channel-correlation.cc')
    reference = load(ROOT / 'reference/figure7.csv')
    provenance = json.loads((ROOT / 'reference/provenance.json').read_text())
    x = load(ROOT / 'results/full/los/run-01/correlation.csv')['distance_lambda']
    baseline = np.array([load(ROOT / 'results/full/los' / f'run-{run:02d}/correlation.csv')['abs_rho'] for run in range(1,11)])
    groups = {'baseline': baseline}
    witnesses = {}
    summaries = []
    max_conjugate = 0
    max_magnitude = 0
    for name in NAMES:
        profile = configuration['profiles'][name]
        curves = []
        witnesses[name] = []
        for run in range(1,11):
            folder = BASE / name / f'run-{run:02d}'
            path = folder / 'correlation.csv'
            record = json.loads((folder / 'execution.json').read_text())
            assert record['returncode'] == record['validation_returncode'] == 0
            assert record['csv_sha256'] == sha(path)
            assert record['witness_sha256'] == sha(Path(str(path)+'.witness.csv'))
            assert record['reverse_sha256'] == sha(Path(str(path)+'.reverse.csv'))
            data = load(path)
            witness = load(Path(str(path)+'.witness.csv'))
            reverse = load(Path(str(path)+'.reverse.csv'))
            assert len(data) == len(reverse) == 163
            assert len(witness) == profile['samples']
            assert np.array_equal(data['distance_lambda'], x)
            assert abs(data['abs_rho'][0]-1) < 1e-10
            assert np.isfinite(data['abs_rho']).all() and np.all(data['abs_rho'] <= 1+1e-10)
            expected_t = np.arange(len(witness)) * .01
            vx, vy = ((.1, 0) if profile['heading_degrees'] == 0 else (0, .1))
            assert np.allclose(witness['time_s'], expected_t, rtol=0, atol=1e-9)
            assert np.allclose(witness['x_m'], 1.1 + vx * expected_t, rtol=0, atol=1e-9)
            assert np.allclose(witness['y_m'], -.6 + vy * expected_t, rtol=0, atol=1e-9)
            assert np.all(witness['z_m'] == 1.73)
            assert np.all(witness['vx_m_s'] == vx) and np.all(witness['vy_m_s'] == vy)
            assert np.unique(witness['channel_generation_s']).size == len(witness)
            assert 'spectrum_cross_checks=3' in (folder / 'execution.log').read_text()
            forward_complex = data['rho_real'] + 1j*data['rho_imag']
            backward_complex = reverse['rho_real'] + 1j*reverse['rho_imag']
            error = float(np.max(abs(backward_complex - np.conj(forward_complex))))
            magnitude_error = float(np.max(abs(reverse['abs_rho']-data['abs_rho'])))
            assert error < 1e-9 and magnitude_error < 1e-9
            max_conjugate = max(max_conjugate, error)
            max_magnitude = max(max_magnitude, magnitude_error)
            witnesses[name].append(witness)
            curves.append(data['abs_rho'])
        groups[name] = np.array(curves)
    for i in range(10):
        a, b = witnesses['control-x'][i], witnesses['control-y'][i]
        assert all(a[field][0] == b[field][0] for field in ['h00_real','h00_imag','clusters'])
        full = witnesses['paper-x-full'][i]
        assert all(np.array_equal(a[field], full[field][:len(a)]) for field in a.dtype.names)
    for name, curves in groups.items():
        mean, sd = curves.mean(axis=0), curves.std(axis=0, ddof=1)
        valid = reference['distance_lambda'] <= x[-1]
        rx, ry = reference['distance_lambda'][valid], reference['abs_rho'][valid]
        error = np.interp(rx, x, mean) - ry
        per_run = [float(np.sqrt(np.mean((np.interp(rx, x, curve)-ry)**2))) for curve in curves]
        summary = dict(profile=name, runs=10, curve_rmse=float(np.sqrt(np.mean(error**2))),
                       curve_mae=float(np.mean(abs(error))), run1_rmse=per_run[0],
                       per_run_rmse=per_run, final_mean=float(mean[-1]), final_sd=float(sd[-1]),
                       landmarks=[dict(actual_lambda=float(x[i]), mean=float(mean[i]), sd=float(sd[i])) for i in [10,20,81,162]])
        summaries.append(summary)
        with (BASE / f'aggregate-{name}.csv').open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['distance_lambda','mean_abs_rho','sd_abs_rho','min_abs_rho','max_abs_rho'])
            writer.writerows(zip(x, mean, sd, curves.min(axis=0), curves.max(axis=0)))
    direction = groups['control-y'] - groups['control-x']
    direction_summary = dict(final_lag_lambda=float(x[-1]),
                             y_minus_x_final_mean=float(direction[:,-1].mean()),
                             y_minus_x_final_sd=float(direction[:,-1].std(ddof=1)),
                             y_lower_final_count=int((direction[:,-1] < 0).sum()),
                             mean_absolute_difference_between_mean_curves=float(np.mean(abs(direction.mean(axis=0)))))
    (BASE / 'summary.json').write_text(json.dumps(summaries, indent=2)+'\n')
    (BASE / 'direction-summary.json').write_text(json.dumps(direction_summary, indent=2)+'\n')
    geometry_difference = np.array(summaries[1]['per_run_rmse']) - np.array(summaries[0]['per_run_rmse'])
    geometry_paired = dict(improved_run_count=int((geometry_difference < 0).sum()),
                           rmse_difference_mean=float(geometry_difference.mean()),
                           rmse_difference_sd=float(geometry_difference.std(ddof=1)))
    (BASE / 'geometry-paired-summary.json').write_text(json.dumps(geometry_paired, indent=2)+'\n')
    for profile in ['baseline-regression','heading-y-check']:
        first = ROOT / 'results/geometry-pilot' / profile / 'run-01/correlation.csv'
        repeat = ROOT / 'results/geometry-repeat' / profile / 'run-01/correlation.csv'
        for suffix in ['', '.witness.csv', '.reverse.csv']:
            assert sha(Path(str(first)+suffix)) == sha(Path(str(repeat)+suffix))
    assert sha(ROOT / 'results/geometry-pilot/baseline-regression/run-01/correlation.csv') == sha(ROOT.parent / 'A3/results/los/correlation.csv')
    validation = dict(passed=True, full_runs=30, spectrum_cross_checks=90,
                      total_lag_reversal_checks=30*163, max_conjugate_error=max_conjugate,
                      max_magnitude_error=max_magnitude, exact_baseline_pilot_match=True,
                      repeated_pilot_profiles=2, matching_initial_direction_channels=10,
                      matching_full_path_prefixes=10)
    (BASE / 'validation.json').write_text(json.dumps(validation, indent=2)+'\n')
    for filename, names in [('geometry-comparison',['baseline','paper-x-full']),
                            ('direction-comparison',['control-x','control-y'])]:
        fig, ax = plt.subplots(figsize=(9,5.5))
        ax.plot(reference['distance_lambda'],reference['abs_rho'],'o--',color='#3030d0',markersize=4,
                label='Paper Fig. 7 (post-print extraction)')
        for name in names:
            curves = groups[name]
            ax.plot(x,curves.mean(axis=0),color=COLORS[name],lw=2.4,label=f'{name}: mean, n=10')
            ax.fill_between(x,curves.min(axis=0),curves.max(axis=0),color=COLORS[name],alpha=.1,
                            label=f'{name}: min–max (not CI)')
        ax.set(xlim=provenance['original_plot_xlim'],ylim=(0,1.02),
               xlabel=r'$\Delta d / \lambda$',ylabel='Correlation magnitude',
               title='Fixed noiseless LOS: '+('initial geometry comparison' if filename.startswith('geometry') else 'equal-length 2.5 m direction controls'))
        ax.set_xticks(np.arange(0,2.01,.25))
        ax.grid(alpha=.25)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(BASE/(filename+'.png'),dpi=180)
        fig.savefig(BASE/(filename+'.pdf'))
        ax.set_ylim(*provenance['original_plot_ylim'])
        fig.savefig(BASE/(filename+'-original-axes.png'),dpi=180)
        plt.close(fig)
    fig, axes = plt.subplots(1,2,figsize=(11,6))
    axes[0].add_patch(Rectangle((1.1,-.6),4.2,2.5,fc='#eff4f8',ec='#777777'))
    axes[0].plot([0,0],[-.6,.6],color='#222222',lw=8,label='Drawn 1.2 m extent (inferred centering)')
    axes[0].plot(0,0,'ks',label='Assumed BS phase center')
    for name in NAMES:
        witness = witnesses[name][0]
        axes[0].plot(witness['x_m'],witness['y_m'],color=COLORS[name],lw=2.4,
                     linestyle='--' if name == 'control-x' else '-', label=name)
        end = len(witness)-1
        before = max(0,end-400)
        axes[0].annotate('', xy=(witness['x_m'][end],witness['y_m'][end]),
                         xytext=(witness['x_m'][before],witness['y_m'][before]),
                         arrowprops=dict(arrowstyle='->',color=COLORS[name],lw=2))
    axes[0].plot(1.1,-.6,'ko',markersize=5,label='Common UE start')
    axes[0].annotate('1.1 m gap assumption',xy=(1.1,-.6),xytext=(.1,-1.0),fontsize=8)
    axes[0].set(xlabel='x (m)',ylabel='y (m)',title='Figure-5-aligned approximation',aspect='equal',xlim=(-.35,5.65),ylim=(2.2,-1.2))
    axes[0].legend(fontsize=7,loc='upper left',bbox_to_anchor=(0,-.16),ncol=2)
    axes[1].plot(x,groups['control-x'][0],color=COLORS['control-x'],label='+x run 1')
    reverse = load(BASE/'control-x/run-01/correlation.csv.reverse.csv')
    axes[1].plot(x,reverse['abs_rho'],'--',color='black',label='Same data in reverse order')
    axes[1].set(xlabel=r'$\Delta d / \lambda$',ylabel='Correlation magnitude',title='Reversal numerical control',ylim=(0,1.02))
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(BASE/'trajectories-and-reversal.png',dpi=180)
    plt.close(fig)
    print(json.dumps(dict(summary=summaries,direction=direction_summary,validation=validation),indent=2))


if __name__ == '__main__':
    main()
