import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    config = json.loads((ROOT / 'results/full/configuration.json').read_text())
    records = json.loads((ROOT / 'results/full/executions.json').read_text())
    assert len(records) == 20
    hashes = []
    for record in records:
        folder = ROOT / 'results/full' / record['condition'] / f'run-{record["run"]:02d}'
        data = folder / 'correlation.csv'
        witness = folder / 'correlation.csv.witness.csv'
        assert sha(data) == record['correlation_sha256']
        assert sha(witness) == record['witness_sha256']
        assert record['returncode'] == 0
        assert len(rows(data)) == 163
        assert len(rows(witness)) == 4201
        assert 'spectrum_cross_checks=3' in (folder / 'execution.log').read_text()
        hashes.append(sha(data))
    assert len(set(hashes)) == 20, 'Channel runs should produce different curves'
    repeat = ROOT / 'results/pilot/los/run-01/correlation.csv'
    primary = ROOT / 'results/full/los/run-01/correlation.csv'
    assert sha(repeat) == sha(primary), 'Same seed/run did not repeat'
    assert sha(Path(str(repeat)+'.witness.csv')) == sha(Path(str(primary)+'.witness.csv'))
    short = ROOT.parent / 'A3/results/los/correlation.csv.witness.csv'
    short_rows = rows(short)
    long_rows = rows(Path(str(primary)+'.witness.csv'))
    assert short_rows == long_rows[:len(short_rows)], 'Short/full trajectories have different prefixes'
    reference = rows(ROOT / 'reference/figure7.csv')
    assert len(reference) == 33
    assert float(reference[0]['distance_lambda']) == 0
    assert float(reference[-1]['distance_lambda']) == 2
    assert config['source_sha256'] == sha(ROOT.parent / 'A3/src/channel-spatial-probe.cc')
    summary = json.loads((ROOT / 'results/summary.json').read_text())
    assert all(item['runs'] == 10 and item['overlap_reference_points'] == 32 for item in summary)
    result = dict(passed=True, full_runs=20, samples_per_run=4201,
                  lags_per_run=163, spectrum_cross_checks_total=60,
                  distinct_curve_hashes=20, repeat_csv_and_witness_identical=True,
                  short_path_prefix_identical=True, reference_vertices=33,
                  reference_points_compared=32)
    (ROOT / 'results/validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
