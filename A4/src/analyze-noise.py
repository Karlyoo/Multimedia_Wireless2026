import csv
import hashlib
import json
import os
from pathlib import Path
import tempfile
import warnings

os.environ.setdefault('MPLCONFIGDIR', tempfile.mkdtemp(prefix='a4-noise-mpl-'))
warnings.filterwarnings('ignore', message='Unable to import Axes3D.*')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/noise'
SETTINGS = [('noiseless', None), ('1', 1), ('6', 6), ('11', 11)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return np.genfromtxt(path, delimiter=',', names=True)


def main():
    config = json.loads((BASE / 'configuration.json').read_text())
    executions = json.loads((BASE / 'executions.json').read_text())
    assert len(executions) == 40
    assert config['exporter_sha256'] == sha(ROOT / 'src/noisy-channel-correlation.cc')
    reference = load(ROOT / 'reference/figure7.csv')
    provenance = json.loads((ROOT / 'reference/provenance.json').read_text())
    results = []
    all_curves = {}
    clean_fields = ['time_s', 'x_m', 'y_m', 'rx_elements', 'tones', 'clusters',
                    'h00_real', 'h00_imag', 'channel_generation_s', 'signal_energy']
    baseline_hashes = []
    realized_errors = []
    paired_channels = {}
    validation_curves = []
    for label, snr in SETTINGS:
        curves = []
        realized = []
        noise_summaries = []
        for run in range(1, 11):
            folder = BASE / 'los' / f'snr-{label}' / f'run-{run:02d}'
            path = folder / 'correlation.csv'
            data = load(path)
            witness = load(Path(str(path) + '.witness.csv'))
            record = json.loads((folder / 'execution.json').read_text())
            assert record['returncode'] == record['validation_returncode'] == 0
            assert record['correlation_sha256'] == sha(path)
            assert record['witness_sha256'] == sha(Path(str(path)+'.witness.csv'))
            assert len(witness) == 4201 and len(data) == 163
            assert abs(witness['time_s'][-1] - 42) < 1e-9
            assert abs(data['abs_rho'][0] - 1) < 1e-10
            assert np.isfinite(data['abs_rho']).all() and np.all(data['abs_rho'] <= 1+1e-10)
            assert 'spectrum_cross_checks=3' in (folder / 'execution.log').read_text()
            if snr is None:
                previous = ROOT / 'results/full/los' / f'run-{run:02d}' / 'correlation.csv'
                assert sha(path) == sha(previous)
                baseline_hashes.append(sha(path))
                paired_channels[run] = witness
            else:
                for field in clean_fields:
                    assert np.array_equal(witness[field], paired_channels[run][field]), field
                low_folder = BASE / 'los/snr-1' / f'run-{run:02d}'
                low = load(low_folder / 'correlation.csv.witness.csv')
                scale = 10 ** ((1-snr)/20)
                for component in ['real', 'imag']:
                    actual = witness[f'observed_h00_{component}'] - witness[f'h00_{component}']
                    expected = (low[f'observed_h00_{component}'] - low[f'h00_{component}']) * scale
                    assert np.allclose(actual, expected, atol=1e-12, rtol=1e-10)
                assert np.allclose(witness['noise_energy'], low['noise_energy'] * scale**2,
                                   rtol=1e-10, atol=1e-9)
            noise_info = json.loads(Path(str(path)+'.noise.json').read_text())
            assert noise_info['enabled'] == (snr is not None)
            assert noise_info['noise_stream'] == 100001
            if snr is not None:
                realized.append(noise_info['realized_snr_db'])
                realized_errors.append(abs(noise_info['realized_snr_db'] - snr))
                assert realized_errors[-1] < .02
                assert noise_info['noise_energy'] > 0
            else:
                assert noise_info['noise_energy'] == 0
                assert np.array_equal(witness['signal_energy'], witness['observation_energy'])
            curves.append(data['abs_rho'])
            noise_summaries.append(noise_info)
            validation_curves.append(sha(path))
        curves = np.array(curves)
        x = data['distance_lambda']
        mean = curves.mean(axis=0)
        sd = curves.std(axis=0, ddof=1)
        all_curves[label] = (curves, mean, sd)
        valid = reference['distance_lambda'] <= x[-1]
        errors = np.interp(reference['distance_lambda'][valid], x, mean) - reference['abs_rho'][valid]
        individual_rmse = [float(np.sqrt(np.mean((np.interp(reference['distance_lambda'][valid], x, curve)
                                                 - reference['abs_rho'][valid])**2))) for curve in curves]
        stats = dict(snr_db=snr, label=label, runs=10,
                     curve_rmse=float(np.sqrt(np.mean(errors**2))), curve_mae=float(np.mean(abs(errors))),
                     per_run_rmse=individual_rmse, run1_rmse=individual_rmse[0],
                     final_mean=float(mean[-1]), final_sd=float(sd[-1]),
                     realized_snr_min=min(realized) if realized else None,
                     realized_snr_max=max(realized) if realized else None)
        stats['landmarks'] = [dict(distance_lambda=float(x[i]), mean=float(mean[i]), sd=float(sd[i]))
                              for i in [1, 10, 20, 81, 162]]
        if snr is not None:
            baseline_rmse = np.array(results[0]['per_run_rmse'])
            difference = np.array(individual_rmse) - baseline_rmse
            stats['paired_rmse_difference_mean'] = float(difference.mean())
            stats['paired_rmse_difference_sd'] = float(difference.std(ddof=1))
            stats['improved_run_count'] = int((difference < 0).sum())
            alpha = 10**(snr/10) / (1+10**(snr/10))
            expected = all_curves['noiseless'][1][1:] * alpha
            stats['nonzero_lag_attenuation_approx_rmse'] = float(np.sqrt(np.mean((mean[1:]-expected)**2)))
        results.append(stats)
        with (BASE / f'aggregate-{label}.csv').open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['distance_lambda', 'mean_abs_rho', 'sd_abs_rho', 'min_abs_rho', 'max_abs_rho'])
            writer.writerows(zip(x, mean, sd, curves.min(axis=0), curves.max(axis=0)))
    for label, snr in SETTINGS:
        first = ROOT / 'results/noise-pilot/los' / f'snr-{label}/run-01/correlation.csv'
        repeat = ROOT / 'results/noise-repeat/los' / f'snr-{label}/run-01/correlation.csv'
        assert sha(first) == sha(repeat)
        assert sha(Path(str(first)+'.witness.csv')) == sha(Path(str(repeat)+'.witness.csv'))
    assert len(set(validation_curves)) == 40
    (BASE / 'summary.json').write_text(json.dumps(results, indent=2) + '\n')
    (BASE / 'validation.json').write_text(json.dumps(dict(
        passed=True, full_runs=40, runs_per_setting=10, samples=4201,
        spectrum_cross_checks=120, noiseless_baseline_hash_matches=len(baseline_hashes),
        channel_witnesses_identical_across_snr=True, common_noise_scaling_verified=True,
        short_repeat_settings=4, distinct_curve_hashes=40,
        max_realized_snr_error_db=max(realized_errors)), indent=2) + '\n')
    colors = {'noiseless':'#087f8c', '1':'#cd4b30', '6':'#d99800', '11':'#2a8250'}
    for name, ylim in [('comparison', [.2, 1]), ('comparison-full-scale', [0, 1.02])]:
        fig, ax = plt.subplots(figsize=(9, 5.5))
        ax.plot(reference['distance_lambda'], reference['abs_rho'], 'o--', color='#3030d0',
                markersize=4, label='Paper Fig. 7 (post-print vector extraction)')
        for label, snr in SETTINGS:
            _, mean, sd = all_curves[label]
            ax.plot(x, mean, lw=2, color=colors[label],
                    label=f'LOS {"noiseless" if snr is None else str(snr)+" dB"}, n=10')
        ax.set(xlim=provenance['original_plot_xlim'], ylim=ylim,
               xlabel=r'$\Delta d$ (normalized to $\lambda$)',
               ylabel='Empirical spatial correlation coefficient',
               title='Noise sensitivity: fixed LOS geometry and paired channel runs')
        ax.set_xticks(np.arange(0, 2.01, .25))
        ax.grid(alpha=.25)
        ax.legend(fontsize=8, loc='upper right')
        fig.tight_layout()
        fig.savefig(BASE / (name + '.png'), dpi=180)
        fig.savefig(BASE / (name + '.pdf'))
        plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), sharex=True, sharey=True)
    for ax, (label, snr) in zip(axes.flat, SETTINGS):
        curves, mean, sd = all_curves[label]
        ax.plot(reference['distance_lambda'], reference['abs_rho'], 'o--', color='#3030d0', markersize=3)
        for curve in curves:
            ax.plot(x, curve, color=colors[label], alpha=.15, lw=.8)
        ax.plot(x, mean, color=colors[label], lw=2)
        ax.set(title='Noiseless' if snr is None else f'{snr} dB', xlim=(0, 2.1875), ylim=(0, 1.02))
        ax.grid(alpha=.2)
    fig.supxlabel(r'$\Delta d / \lambda$')
    fig.supylabel('Correlation magnitude')
    fig.suptitle('All predeclared runs; bold = mean, thin = individual realization')
    fig.tight_layout()
    fig.savefig(BASE / 'per-run-comparison.png', dpi=180)
    plt.close(fig)
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
