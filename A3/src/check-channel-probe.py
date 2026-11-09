"""Validate probe invariants and plot our simulated result (no paper curve implied)."""
import argparse
import csv
import math
import warnings
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("csv", type=Path)
parser.add_argument("--plot", type=Path)
args = parser.parse_args()
with args.csv.open(newline="") as stream:
    rows = list(csv.DictReader(stream))
assert len(rows) > 10, "Too few lags"
assert int(rows[0]["lag_samples"]) == 0
assert abs(float(rows[0]["abs_rho"]) - 1) < 1e-10, "rho(0) != 1"
for index, row in enumerate(rows):
    value = float(row["abs_rho"])
    assert math.isfinite(value) and 0 <= value <= 1 + 1e-10
    assert abs(value - math.hypot(float(row["rho_real"]), float(row["rho_imag"]))) < 1e-10
    assert int(row["lag_samples"]) == index
    assert int(row["pairs"]) > 0
assert abs(float(rows[-1]["distance_lambda"]) - 2) < 0.02
with Path(str(args.csv) + ".witness.csv").open(newline="") as stream:
    witness = list(csv.DictReader(stream))
assert len(witness) == int(rows[0]["pairs"])
assert len({row["channel_generation_s"] for row in witness}) > 1, "No channel updates"
assert len({(row["h00_real"], row["h00_imag"]) for row in witness}) > 1, "Frozen CFR"
print(f"PASS: {len(witness)} snapshots; {len(rows)} lags; finite complex CFR; rho(0)=1; updates observed")
print(f"abs_rho at last lag ({float(rows[-1]['distance_lambda']):.3f} lambda): {float(rows[-1]['abs_rho']):.6f}")
if args.plot:
    warnings.filterwarnings("ignore", message="Unable to import Axes3D.*", category=UserWarning)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot([float(row["distance_lambda"]) for row in rows],
            [float(row["abs_rho"]) for row in rows], label="ns-3 readiness probe")
    ax.set(xlabel=r"Separation $\Delta d/\lambda$", ylabel=r"$|\rho(\Delta d)|$",
           xlim=(0, 2), ylim=(0, 1.02), title="Simulated channel check — paper overlay pending")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.plot, dpi=160)
    plt.close(fig)
