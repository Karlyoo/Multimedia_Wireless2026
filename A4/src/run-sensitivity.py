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
    'height-1.73': dict(height_m=1.73, bearing_degrees=0),
    'height-3.0': dict(height_m=3.0, bearing_degrees=0),
    'bearing-minus30': dict(height_m=2.5, bearing_degrees=-30),
    'bearing-plus30': dict(height_m=2.5, bearing_degrees=30),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ns3', type=Path, default=Path('/home/karl/projects/ns-3.48-nr'))
    parser.add_argument('--runs', type=int, default=5)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--pilot', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.runs < 1 or args.workers < 1:
        parser.error('Positive run/worker counts required')
    output = args.output or ROOT / 'results' / ('sensitivity-pilot' if args.pilot else 'sensitivity')
    if output.resolve() in [(ROOT/'results'/name).resolve() for name in ['full','noise','geometry']]:
        parser.error('Do not overwrite existing experiments')
    output.mkdir(parents=True, exist_ok=True)
    profiles = {name:dict(samples=4201, ue_x=1.1, ue_y=-.6, **values) for name,values in PROFILES.items()}
    run_ids = list(range(1,args.runs+1))
    if args.pilot:
        profiles = {
            'original-short': dict(samples=257,ue_x=2,ue_y=2,height_m=2.5,bearing_degrees=0),
            'reference-full': dict(samples=4201,ue_x=1.1,ue_y=-.6,height_m=2.5,bearing_degrees=0),
            'bearing-check': dict(samples=257,ue_x=1.1,ue_y=-.6,height_m=2.5,bearing_degrees=-30),
        }
        run_ids = [1]
    build = Path(tempfile.mkdtemp(prefix='a4-sensitivity-build-'))
    executable = build / 'channel-correlation'
    source = ROOT / 'src/sensitivity-channel-correlation.cc'
    command = ['/usr/bin/g++-12','-B/usr/bin/','-std=c++23','-O2',
               '-DNS3_ASSERT_ENABLE','-DNS3_LOG_ENABLE',f'-I{args.ns3}/build/include',
               '-I/usr/include/eigen3',str(source),f'-L{args.ns3}/build/lib',
               f'-Wl,-rpath,{args.ns3}/build/lib','-Wl,-rpath-link,/usr/lib/x86_64-linux-gnu',
               *[f'-lns3.48-{m}-default' for m in ['spectrum','propagation','mobility','network','antenna','core']],
               '-o',str(executable)]
    subprocess.run(command,check=True)
    config = dict(profiles=profiles,seed=20261109,run_ids=run_ids,stream_start=1,
                  noise=False,scenario='InH-OfficeMixed',condition='LOS',
                  speed_m_s=.1,snapshot_interval_s=.01,step_m=.001,
                  frequency_hz=3.7e9,bs_array=[4,25],spacing_lambda=.5,
                  tones=100,tone_spacing_hz=180000,bs_xy_m=[0,0],ue_height_m=1.73,
                  bs_downtilt_rad=0,source_sha256=sha(source),compile_command=command,
                  compiler=subprocess.check_output(['/usr/bin/g++-12','--version'],text=True).splitlines()[0],
                  ns3_commit=subprocess.check_output(['git','-C',str(args.ns3),'rev-parse','HEAD'],text=True).strip(),
                  workers=args.workers,reference='Existing geometry/paper-x-full runs, matching IDs only',
                  purpose='Exploratory one-factor-at-a-time height/bearing sensitivity; not parameter estimation')
    (output/'configuration.json').write_text(json.dumps(config,indent=2)+'\n')

    def execute(task):
        name,run = task
        p = profiles[name]
        folder = output/name/f'run-{run:02d}'
        folder.mkdir(parents=True,exist_ok=True)
        path = folder/'correlation.csv'
        cmd = [str(executable),'--seed=20261109',f'--run={run}','--nlos=0',
               f'--samples={p["samples"]}',f'--ueX={p["ue_x"]}',f'--ueY={p["ue_y"]}',
               f'--bsHeight={p["height_m"]}',f'--bearingDegrees={p["bearing_degrees"]}',f'--output={path}']
        begin = time.monotonic()
        with (folder/'execution.log').open('w') as log:
            result = subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
            check = subprocess.run(['python3',str(ROOT.parent/'A3/src/check-channel-probe.py'),str(path)],
                                   stdout=log,stderr=subprocess.STDOUT) if result.returncode == 0 else None
        record = dict(profile=name,run=run,command=cmd,returncode=result.returncode,
                      validation_returncode=check.returncode if check else None,
                      wall_seconds=time.monotonic()-begin)
        if result.returncode == 0:
            record.update(csv_sha256=sha(path),witness_sha256=sha(Path(str(path)+'.witness.csv')))
        (folder/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps(record),flush=True)
        if result.returncode or record['validation_returncode'] != 0:
            raise RuntimeError(f'Failed {name} / {run}; inspect execution.log')
        return record

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        records = list(pool.map(execute,[(name,run) for name in profiles for run in run_ids]))
    (output/'executions.json').write_text(json.dumps(records,indent=2)+'\n')
    print(f'Validated {len(records)} runs. Executable retained at {executable}',flush=True)


if __name__ == '__main__':
    main()
