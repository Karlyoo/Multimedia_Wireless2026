import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ns3',type=Path,default=Path('/home/karl/projects/ns-3.48-nr'))
    parser.add_argument('--runs',type=int,default=10)
    parser.add_argument('--output',type=Path,default=ROOT/'results/figure6')
    args = parser.parse_args()
    if args.runs < 1:
        parser.error('Positive run count required')
    args.output.mkdir(parents=True,exist_ok=True)
    build = Path(tempfile.mkdtemp(prefix='a4-figure6-build-'))
    executable = build/'figure6-channel'
    source = ROOT/'src/figure6-channel.cc'
    compile_command = ['/usr/bin/g++-12','-B/usr/bin/','-std=c++23','-O2',
                       '-DNS3_ASSERT_ENABLE','-DNS3_LOG_ENABLE',f'-I{args.ns3}/build/include',
                       '-I/usr/include/eigen3',str(source),f'-L{args.ns3}/build/lib',
                       f'-Wl,-rpath,{args.ns3}/build/lib','-Wl,-rpath-link,/usr/lib/x86_64-linux-gnu',
                       *[f'-lns3.48-{m}-default' for m in ['spectrum','propagation','mobility','network','antenna','core']],
                       '-o',str(executable)]
    subprocess.run(compile_command,check=True)
    config = dict(seed=20261109,run_ids=list(range(1,args.runs+1)),stream_start=1,
                  source_sha256=sha(source),compile_command=compile_command,
                  ns3_commit=subprocess.check_output(['git','-C',str(args.ns3),'rev-parse','HEAD'],text=True).strip(),
                  compiler=subprocess.check_output(['/usr/bin/g++-12','--version'],text=True).splitlines()[0],
                  ue_position_m=[3.19,.42,1.73],bs_position_m=[0,0,2.5],
                  position_note='Schematic Figure 5 point-A estimate; not surveyed original coordinates.',
                  stationary=True,observation_time_s=0,noise=False,condition='LOS',scenario='InH-OfficeMixed',
                  carrier_hz=3.7e9,tones=100,tone_spacing_hz=180000,bs_array=[4,25],
                  antenna_spacing_lambda=.5,bs_bearing_rad=0,bs_downtilt_rad=0,
                  delay_bin_s=1/(100*180000),delay_period_s=1/180000,
                  display_run=1,display_normalization='Each map: 10 log10(power / global map peak); no per-antenna normalization.')
    (args.output/'configuration.json').write_text(json.dumps(config,indent=2)+'\n')
    records = []
    for run in [*config['run_ids'],1]:
        repeat = len(records) == args.runs
        folder = args.output/('repeat-run-01' if repeat else f'run-{run:02d}')
        folder.mkdir(parents=True,exist_ok=True)
        path = folder/'channel.csv'
        command = [str(executable),'--seed=20261109',f'--run={run}',f'--output={path}']
        begin = time.monotonic()
        with (folder/'execution.log').open('w') as log:
            process = subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
        record = dict(run=run,repeat=repeat,returncode=process.returncode,
                      wall_seconds=time.monotonic()-begin,command=command)
        if process.returncode == 0:
            record.update(channel_sha256=sha(path),cluster_sha256=sha(Path(str(path)+'.clusters.csv')))
        (folder/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
        records.append(record)
        print(json.dumps(record),flush=True)
        if process.returncode:
            raise RuntimeError(f'Failed run {run}; see execution.log')
    assert records[0]['channel_sha256'] == records[-1]['channel_sha256']
    assert records[0]['cluster_sha256'] == records[-1]['cluster_sha256']
    (args.output/'executions.json').write_text(json.dumps(records,indent=2)+'\n')
    print(f'Completed {args.runs} static runs and one identical repeat; executable: {executable}')


if __name__ == '__main__':
    main()
