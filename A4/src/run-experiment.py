import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ns3', type=Path, default=Path('/home/karl/projects/ns-3.48-nr'))
    parser.add_argument('--samples', type=int, default=4201)
    parser.add_argument('--runs', type=int, default=10)
    parser.add_argument('--conditions', nargs='+', choices=['los', 'nlos'], default=['los', 'nlos'])
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--noise-study', action='store_true')
    args = parser.parse_args()
    if args.runs < 1 or args.workers < 1 or args.samples < 2:
        parser.error('Positive runs/workers and at least two samples required')
    if args.output is None:
        args.output = ROOT / 'results' / ('noise' if args.noise_study else 'full')
    if args.noise_study:
        args.conditions = ['los']
        if args.output.resolve() == (ROOT / 'results/full').resolve():
            parser.error('Noise study must not overwrite the original full batch')
    args.output.mkdir(parents=True, exist_ok=True)
    build = Path(tempfile.mkdtemp(prefix='a4-channel-build-'))
    executable = build / 'channel-correlation'
    source = ROOT / 'src' / ('noisy-channel-correlation.cc' if args.noise_study else 'channel-correlation.cc')
    compile_cmd = ['/usr/bin/g++-12', '-B/usr/bin/', '-std=c++23', '-O2', '-DNS3_ASSERT_ENABLE', '-DNS3_LOG_ENABLE',
                   f'-I{args.ns3}/build/include', '-I/usr/include/eigen3',
                   str(source), f'-L{args.ns3}/build/lib',
                   f'-Wl,-rpath,{args.ns3}/build/lib', '-Wl,-rpath-link,/usr/lib/x86_64-linux-gnu',
                   *[f'-lns3.48-{module}-default' for module in ['spectrum', 'propagation', 'mobility', 'network', 'antenna', 'core']],
                   '-o', str(executable)]
    subprocess.run(compile_cmd, check=True)
    manifest = dict(seed=20261109, run_ids=list(range(1, args.runs + 1)), stream_start=1,
                    samples=args.samples, simulated_seconds=(args.samples - 1) * .01,
                    sample_interval_s=.01, speed_m_s=.1, step_m=.001,
                    frequency_hz=3.7e9, tones=100, tone_spacing_hz=180000,
                    bs_rows=4, bs_columns=25, bs_position_m=[0, 0, 2.5],
                    ue_initial_position_m=[2, 2, 1.73], scenario='InH-OfficeMixed',
                    conditions=args.conditions, workers=args.workers,
                    ns3_commit=subprocess.check_output(['git', '-C', str(args.ns3), 'rev-parse', 'HEAD'], text=True).strip(),
                    source_sha256=digest(REPO / 'A3/src/channel-spatial-probe.cc'),
                    compiler=subprocess.check_output(['g++-12', '--version'], text=True).splitlines()[0],
                    compile_command=compile_cmd)
    if args.noise_study:
        manifest.update(noise_stream=100001, snr_db=[None, 1, 6, 11],
                        noise_model='Independent circular complex Gaussian, before normalization; per-snapshot average signal power sets expected SNR; common channel and normal draws across SNRs.',
                        exporter_sha256=digest(source))
    (args.output / 'configuration.json').write_text(json.dumps(manifest, indent=2) + '\n')

    def execute(task):
        condition, run, snr = task
        folder = args.output / condition
        if args.noise_study:
            folder = folder / ('snr-noiseless' if snr is None else f'snr-{snr}')
        folder = folder / f'run-{run:02d}'
        folder.mkdir(parents=True, exist_ok=True)
        output = folder / 'correlation.csv'
        cmd = [str(executable), '--seed=20261109', f'--run={run}', f'--samples={args.samples}',
               f'--nlos={int(condition == "nlos")}', f'--output={output}']
        if args.noise_study:
            cmd += [f'--noise={int(snr is not None)}', f'--snrDb={snr if snr is not None else 6}', '--noiseStream=100001']
        begin = time.monotonic()
        with (folder / 'execution.log').open('w') as log:
            process = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
            if process.returncode == 0:
                validation = subprocess.run(['python3', str(REPO / 'A3/src/check-channel-probe.py'), str(output)],
                                            stdout=log, stderr=subprocess.STDOUT)
            else:
                validation = None
        record = dict(condition=condition, run=run, returncode=process.returncode,
                      wall_seconds=time.monotonic() - begin, command=cmd)
        record['validation_returncode'] = validation.returncode if validation else None
        if args.noise_study:
            record['snr_db'] = snr
        if process.returncode == 0:
            record['correlation_sha256'] = digest(output)
            record['witness_sha256'] = digest(Path(str(output) + '.witness.csv'))
        (folder / 'execution.json').write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps(record), flush=True)
        if process.returncode or record['validation_returncode'] != 0:
            raise RuntimeError(f'Failed: {condition}, run {run}; see {folder}/execution.log')
        return record

    tasks = [(condition, run, snr) for condition in args.conditions
             for run in range(1, args.runs + 1)
             for snr in ([None, 1, 6, 11] if args.noise_study else [None])]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        records = list(pool.map(execute, tasks))
    (args.output / 'executions.json').write_text(json.dumps(records, indent=2) + '\n')
    print(f'Validated {len(records)} runs. Build retained at {build}', flush=True)


if __name__ == '__main__':
    main()
