import csv
import hashlib
import json
import os
from pathlib import Path
import tempfile
import warnings

os.environ.setdefault('MPLCONFIGDIR',tempfile.mkdtemp(prefix='a4-sensitivity-mpl-'))
warnings.filterwarnings('ignore',message='Unable to import Axes3D.*')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'results/sensitivity'
NAMES = ['reference','height-1.73','height-3.0','bearing-minus30','bearing-plus30']
COLORS = ['#333333','#087f8c','#d07a00','#954b9c','#497d2b']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return np.genfromtxt(path,delimiter=',',names=True)


def main():
    config = json.loads((BASE/'configuration.json').read_text())
    executions = json.loads((BASE/'executions.json').read_text())
    assert len(executions) == 20 and config['run_ids'] == [1,2,3,4,5]
    assert config['source_sha256'] == sha(ROOT/'src/sensitivity-channel-correlation.cc')
    reference = load(ROOT/'reference/figure7.csv')
    provenance = json.loads((ROOT/'reference/provenance.json').read_text())
    groups = {}
    results = []
    reference_files = []
    for name in NAMES:
        curves = []
        for run in config['run_ids']:
            if name == 'reference':
                folder = ROOT/'results/geometry/paper-x-full'/f'run-{run:02d}'
                profile = dict(height_m=2.5,bearing_degrees=0)
            else:
                folder = BASE/name/f'run-{run:02d}'
                profile = config['profiles'][name]
            path = folder/'correlation.csv'
            record = json.loads((folder/'execution.json').read_text())
            assert record['returncode'] == record['validation_returncode'] == 0
            assert sha(path) == record['csv_sha256']
            assert sha(Path(str(path)+'.witness.csv')) == record['witness_sha256']
            data = load(path)
            witness = load(Path(str(path)+'.witness.csv'))
            assert len(data) == 163 and len(witness) == 4201
            assert np.allclose(witness['x_m'],1.1+.001*np.arange(4201),rtol=0,atol=1e-9)
            assert np.all(witness['y_m'] == -.6)
            assert abs(witness['time_s'][-1]-42) < 1e-9
            assert abs(data['abs_rho'][0]-1) < 1e-10
            assert np.isfinite(data['abs_rho']).all() and np.all(data['abs_rho'] <= 1+1e-10)
            assert np.unique(witness['channel_generation_s']).size == 4201
            assert 'spectrum_cross_checks=3' in (folder/'execution.log').read_text()
            if name == 'reference':
                reference_files.append(dict(run=run,path=str(path.relative_to(ROOT)),sha256=sha(path)))
            else:
                assert np.all(witness['bs_height_m'] == profile['height_m'])
                assert np.all(witness['bs_bearing_degrees'] == profile['bearing_degrees'])
            if curves:
                assert np.array_equal(x,data['distance_lambda'])
            x = data['distance_lambda']
            curves.append(data['abs_rho'])
        curves = np.array(curves)
        groups[name] = curves
        mean,sd = curves.mean(axis=0),curves.std(axis=0,ddof=1)
        valid = reference['distance_lambda'] <= x[-1]
        rx,ry = reference['distance_lambda'][valid],reference['abs_rho'][valid]
        errors = np.interp(rx,x,mean)-ry
        per_run = np.array([np.sqrt(np.mean((np.interp(rx,x,c)-ry)**2)) for c in curves])
        item = dict(profile=name,height_m=profile['height_m'],bearing_degrees=profile['bearing_degrees'],
                    runs=5,curve_rmse=float(np.sqrt(np.mean(errors**2))),curve_mae=float(abs(errors).mean()),
                    per_run_rmse=per_run.tolist(),individual_rmse_mean=float(per_run.mean()),
                    final_mean=float(mean[-1]),final_sd=float(sd[-1]),
                    landmarks=[dict(actual_lambda=float(x[i]),mean=float(mean[i]),sd=float(sd[i])) for i in [10,20,81,162]])
        if name != 'reference':
            difference = per_run-np.array(results[0]['per_run_rmse'])
            item.update(paired_rmse_difference_mean=float(difference.mean()),
                        paired_rmse_difference_sd=float(difference.std(ddof=1)),
                        improved_runs=int((difference<0).sum()),
                        maximum_mean_curve_difference=float(np.max(abs(mean-groups['reference'].mean(axis=0)))))
        results.append(item)
        with (BASE/f'aggregate-{name}.csv').open('w',newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['distance_lambda','mean_abs_rho','sd_abs_rho','min_abs_rho','max_abs_rho'])
            writer.writerows(zip(x,mean,sd,curves.min(axis=0),curves.max(axis=0)))
    assert sha(ROOT/'results/sensitivity-pilot/original-short/run-01/correlation.csv') == sha(ROOT.parent/'A3/results/los/correlation.csv')
    assert sha(ROOT/'results/sensitivity-pilot/reference-full/run-01/correlation.csv') == sha(ROOT/'results/geometry/paper-x-full/run-01/correlation.csv')
    for profile in ['original-short','reference-full','bearing-check']:
        record = json.loads((ROOT/'results/sensitivity-pilot'/profile/'run-01/execution.json').read_text())
        assert record['returncode'] == record['validation_returncode'] == 0
    (BASE/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
    (BASE/'reference-inputs.json').write_text(json.dumps(reference_files,indent=2)+'\n')
    (BASE/'validation.json').write_text(json.dumps(dict(passed=True,new_full_runs=20,
        reused_reference_runs=5,compared_runs_per_setting=5,samples=4201,lags=163,
        full_spectrum_checks=60,pilot_runs=3,short_regression_identical=True,
        full_reference_regression_identical=True,only_height_or_bearing_changed=True),indent=2)+'\n')
    with (BASE/'metrics.csv').open('w',newline='') as stream:
        fields = ['profile','height_m','bearing_degrees','runs','curve_rmse','curve_mae',
                  'individual_rmse_mean','paired_rmse_difference_mean','paired_rmse_difference_sd',
                  'improved_runs','final_mean','final_sd']
        writer = csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)
    for group_name,names in [('height',['reference','height-1.73','height-3.0']),
                             ('bearing',['reference','bearing-minus30','bearing-plus30'])]:
        fig,ax = plt.subplots(figsize=(9,5.5))
        ax.plot(reference['distance_lambda'],reference['abs_rho'],'o--',color='#3030d0',markersize=4,
                label='Paper Fig. 7 (post-print extraction)')
        for name in names:
            color = COLORS[NAMES.index(name)]
            curves = groups[name]
            ax.plot(x,curves.mean(axis=0),color=color,lw=2.3,label=f'{name}: mean, n=5')
            ax.fill_between(x,curves.min(axis=0),curves.max(axis=0),color=color,alpha=.09,
                            label=f'{name}: min–max (not CI)')
        ax.set(xlim=provenance['original_plot_xlim'],ylim=(0,1.02),xlabel=r'$\Delta d / \lambda$',
               ylabel='Correlation magnitude',title=f'One-factor {group_name} sensitivity: fixed noiseless LOS trajectory')
        ax.set_xticks(np.arange(0,2.01,.25))
        ax.grid(alpha=.25)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(BASE/f'{group_name}-comparison.png',dpi=180)
        fig.savefig(BASE/f'{group_name}-comparison.pdf')
        ax.set_ylim(*provenance['original_plot_ylim'])
        fig.savefig(BASE/f'{group_name}-original-axes.png',dpi=180)
        plt.close(fig)
    print(json.dumps(results,indent=2))


if __name__ == '__main__':
    main()
