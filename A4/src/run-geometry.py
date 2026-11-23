import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {
    'paper-x-full': dict(samples=4201, ue_x=1.1, ue_y=-.6, heading_degrees=0),
    'control-x': dict(samples=2501, ue_x=1.1, ue_y=-.6, heading_degrees=0),
    'control-y': dict(samples=2501, ue_x=1.1, ue_y=-.6, heading_degrees=90),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ns3', type=Path, default=Path('/home/karl/projects/ns-3.48-nr'))
    parser.add_argument('--runs', type=int, default=10)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--pilot', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.runs < 1 or args.workers < 1:
        parser.error('Positive run and worker counts required')
    output = args.output or ROOT / 'results' / ('geometry-pilot' if args.pilot else 'geometry')
    if output.resolve() in [(ROOT / 'results' / n).resolve() for n in ['full', 'noise']]:
        parser.error('Do not overwrite baseline or noise experiments')
    output.mkdir(parents=True, exist_ok=True)
    profiles = dict(PROFILES)
    if args.pilot:
        profiles = {
            'baseline-regression': dict(samples=257, ue_x=2, ue_y=2, heading_degrees=0),
            'heading-y-check': dict(samples=257, ue_x=1.1, ue_y=-.6, heading_degrees=90),
        }
    build = Path(tempfile.mkdtemp(prefix='a4-geometry-build-'))
    executable = build / 'channel-correlation'
    source = ROOT / 'src/geometry-channel-correlation.cc'
    compile_command = ['/usr/bin/g++-12', '-B/usr/bin/', '-std=c++23', '-O2',
                       '-DNS3_ASSERT_ENABLE', '-DNS3_LOG_ENABLE',
                       f'-I{args.ns3}/build/include', '-I/usr/include/eigen3', str(source),
                       f'-L{args.ns3}/build/lib', f'-Wl,-rpath,{args.ns3}/build/lib',
                       '-Wl,-rpath-link,/usr/lib/x86_64-linux-gnu',
                       *[f'-lns3.48-{name}-default' for name in ['spectrum', 'propagation', 'mobility', 'network', 'antenna', 'core']],
                       '-o', str(executable)]
    subprocess.run(compile_command, check=True)
    configuration = dict(profiles=profiles, seed=20261109, run_ids=list(range(1, args.runs+1)),
                         stream_start=1, speed_m_s=.1, step_m=.001, snapshot_interval_s=.01,
                         bs_position_m=[0, 0, 2.5], ue_height_m=1.73, noise=False,
                         bs_array=[4, 25], spacing_lambda=.5, frequency_hz=3.7e9,
                         tones=100, tone_spacing_hz=180000, scenario='InH-OfficeMixed', condition='LOS',
                         bs_bearing_rad=0, bs_downtilt_rad=0, update_period_s=.005,
                         geometry_note='Figure-5-aligned approximation: inferred lateral phase-center offset and face-plane convention; BS height remains assumed.',
                         source_sha256=sha(source), compiler=subprocess.check_output(['/usr/bin/g++-12', '--version'], text=True).splitlines()[0],
                         ns3_commit=subprocess.check_output(['git', '-C', str(args.ns3), 'rev-parse', 'HEAD'], text=True).strip(),
                         workers=args.workers, compile_command=compile_command)
    (output / 'configuration.json').write_text(json.dumps(configuration, indent=2)+'\n')

    def execute(task):
        name, run = task
        profile = profiles[name]
        folder = output / name / f'run-{run:02d}'
        folder.mkdir(parents=True, exist_ok=True)
        csv_path = folder / 'correlation.csv'
        command = [str(executable), '--seed=20261109', f'--run={run}', '--nlos=0',
                   f'--samples={profile["samples"]}', f'--ueX={profile["ue_x"]}',
                   f'--ueY={profile["ue_y"]}', f'--headingDegrees={profile["heading_degrees"]}',
                   f'--output={csv_path}']
        begin = time.monotonic()
        with (folder / 'execution.log').open('w') as log:
            process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
            validation = subprocess.run(['python3', str(ROOT.parent / 'A3/src/check-channel-probe.py'), str(csv_path)],
                                        stdout=log, stderr=subprocess.STDOUT) if process.returncode == 0 else None
        record = dict(profile=name, run=run, command=command, returncode=process.returncode,
                      validation_returncode=validation.returncode if validation else None,
                      wall_seconds=time.monotonic()-begin)
        if process.returncode == 0:
            record['csv_sha256'] = sha(csv_path)
            record['witness_sha256'] = sha(Path(str(csv_path)+'.witness.csv'))
            record['reverse_sha256'] = sha(Path(str(csv_path)+'.reverse.csv'))
        (folder / 'execution.json').write_text(json.dumps(record, indent=2)+'\n')
        print(json.dumps(record), flush=True)
        if process.returncode or record['validation_returncode'] != 0:
            raise RuntimeError(f'Failed {name}, run {run}; see execution.log')
        return record

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        records = list(pool.map(execute, [(name, run) for name in profiles for run in configuration['run_ids']]))
    (output / 'executions.json').write_text(json.dumps(records, indent=2)+'\n')
    print(f'Validated {len(records)} geometry runs; executable retained at {executable}', flush=True)


if __name__ == '__main__':
    main()
