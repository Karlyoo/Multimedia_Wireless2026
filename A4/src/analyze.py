import argparse
import csv
import json
import os
from pathlib import Path
import tempfile
import warnings

os.environ.setdefault('MPLCONFIGDIR', tempfile.mkdtemp(prefix='a4-mpl-'))
warnings.filterwarnings('ignore', message='Unable to import Axes3D.*')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return np.genfromtxt(path, delimiter=',', names=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'results/full')
    args = parser.parse_args()
    output = ROOT / 'results'
    config = json.loads((args.input / 'configuration.json').read_text())
    reference = load(ROOT / 'reference/figure7.csv')
    provenance = json.loads((ROOT / 'reference/provenance.json').read_text())
    datasets = {}
    summaries = []
    comparisons = []
    for condition in config['conditions']:
        curves = []
        for run in config['run_ids']:
            folder = args.input / condition / f'run-{run:02d}'
            record = json.loads((folder / 'execution.json').read_text())
            assert record['returncode'] == 0
            data = load(folder / 'correlation.csv')
            witness = load(folder / 'correlation.csv.witness.csv')
            assert len(witness) == config['samples']
            assert abs(witness['time_s'][-1] - config['simulated_seconds']) < 1e-9
            assert np.allclose(np.diff(witness['x_m']), .001)
            assert np.isfinite(data['abs_rho']).all()
            assert np.all(data['abs_rho'] <= 1+1e-10)
            assert abs(data['abs_rho'][0] - 1) < 1e-10
            if curves:
                assert np.array_equal(x, data['distance_lambda'])
            x = data['distance_lambda']
            curves.append(data['abs_rho'])
        curves = np.array(curves)
        mean = curves.mean(axis=0)
        sd = curves.std(axis=0, ddof=1)
        low, high = curves.min(axis=0), curves.max(axis=0)
        datasets[condition] = (x, curves, mean, sd, low, high)
        with (output / f'{condition}-aggregate.csv').open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['distance_lambda', 'mean_abs_rho', 'sd_abs_rho', 'min_abs_rho', 'max_abs_rho', 'runs'])
            writer.writerows(zip(x, mean, sd, low, high, [len(curves)] * len(x)))
        valid = reference['distance_lambda'] <= x[-1]
        rx, ry = reference['distance_lambda'][valid], reference['abs_rho'][valid]
        prediction = np.interp(rx, x, mean)
        single_prediction = np.interp(rx, x, curves[0])
        summaries.append(dict(condition=condition, runs=len(curves),
                              overlap_reference_points=int(valid.sum()),
                              curve_rmse=float(np.sqrt(np.mean((prediction-ry)**2))),
                              curve_mae=float(np.mean(np.abs(prediction-ry))),
                              run1_curve_rmse=float(np.sqrt(np.mean((single_prediction-ry)**2))),
                              final_lag_lambda=float(x[-1]), final_mean=float(mean[-1]),
                              final_sd=float(sd[-1]), final_min=float(low[-1]), final_max=float(high[-1])))
        for dx, ref, sim in zip(rx, ry, prediction):
            comparisons.append([condition, dx, ref, sim, sim-ref])
        for target in [.125, .25, .5, 1, 1.5, 2]:
            idx = int(np.argmin(abs(x-target)))
            summaries[-1].setdefault('landmarks', []).append(dict(target_lambda=target, actual_lambda=float(x[idx]),
                                                               paper_interpolated=float(np.interp(x[idx], reference['distance_lambda'], reference['abs_rho'])),
                                                               mean=float(mean[idx]), sd=float(sd[idx])))
    with (output / 'reference-comparison.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['condition', 'distance_lambda', 'paper_abs_rho', 'simulation_mean', 'difference'])
        writer.writerows(comparisons)
    (output / 'summary.json').write_text(json.dumps(summaries, indent=2) + '\n')
    plt.rcParams.update({'font.size': 11})
    colors = {'los': '#087f8c', 'nlos': '#d56b20'}
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(reference['distance_lambda'], reference['abs_rho'], 'o--', color='#3030d0',
            markersize=4, label='Paper Fig. 7 (post-print vector extraction)')
    x, curves, *_ = datasets['los']
    ax.plot(x, curves[0], color=colors['los'], lw=2,
            label='ns-3 LOS, preselected run 1, 42 s')
    ax.set(xlim=provenance['original_plot_xlim'], ylim=provenance['original_plot_ylim'],
           xlabel=r'$\Delta d$ (normalized to $\lambda$)',
           ylabel='Empirical spatial correlation coefficient',
           title='Fig. 7 reconstruction: single measured vs. single simulated trajectory')
    ax.set_xticks(np.arange(0, 2.01, .25))
    ax.grid(alpha=.25)
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(output / 'figure7-single-run.png', dpi=180)
    fig.savefig(output / 'figure7-single-run.pdf')
    plt.close(fig)
    for name, limits, conditions in [('figure7-overlay', provenance['original_plot_ylim'], ['los']),
                                     ('sensitivity-full-scale', [0, 1.02], list(datasets))]:
        fig, ax = plt.subplots(figsize=(9, 5.5))
        ax.plot(reference['distance_lambda'], reference['abs_rho'], 'o--', color='#3030d0',
                markersize=4, label='Paper Fig. 7 (post-print vector extraction)', zorder=5)
        for condition in conditions:
            x, curves, mean, sd, low, high = datasets[condition]
            color = colors[condition]
            for i, curve in enumerate(curves):
                ax.plot(x, curve, color=color, alpha=.14, lw=.7)
            ax.fill_between(x, low, high, color=color, alpha=.12,
                            label=f'{condition.upper()} across-run min–max (not CI)')
            ax.plot(x, mean, color=color, lw=2.5, label=f'ns-3 {condition.upper()} mean, n={len(curves)}')
        ax.set(xlim=provenance['original_plot_xlim'], ylim=limits,
               xlabel=r'$\Delta d$ (normalized to $\lambda$)',
               ylabel='Empirical spatial correlation coefficient',
               title='Fig. 7 reconstruction: measured studio vs. statistical indoor model')
        ax.set_xticks(np.arange(0, 2.01, .25))
        ax.grid(alpha=.25)
        ax.legend(fontsize=8, loc='lower right')
        fig.tight_layout()
        fig.savefig(output / (name + '.png'), dpi=180)
        fig.savefig(output / (name + '.pdf'))
        plt.close(fig)
    print(json.dumps(summaries, indent=2))


if __name__ == '__main__':
    main()
