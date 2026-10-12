#!/usr/bin/env python3
"""Plot the PDF/PMF and CDF files produced by xr-pose-uplink."""

import argparse
import csv
import os
import tempfile
import warnings
from pathlib import Path

# Avoid warnings when the user's default Matplotlib cache is read-only.
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "matplotlib-xr-pose"))
import matplotlib

# This script only writes PNG files; a GUI/Wayland backend is unnecessary.
matplotlib.use("Agg")
warnings.filterwarnings("ignore", message="Unable to import Axes3D.*")
import matplotlib.pyplot as plt


def read_columns(path: Path, x_name: str, y_name: str):
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    return ([float(row[x_name]) for row in rows], [float(row[y_name]) for row in rows])


def read_packet_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default="xr-pose-uplink")
    args = parser.parse_args()
    prefix = Path(args.prefix)

    size_x, size_pdf = read_columns(
        Path(f"{prefix}-size-pdf.csv"), "ip_bytes", "probability"
    )
    size_cdf_x, size_cdf = read_columns(
        Path(f"{prefix}-size-cdf.csv"), "ip_bytes", "cdf"
    )
    interval_x, interval_pdf = read_columns(
        Path(f"{prefix}-interval-pdf.csv"), "send_interval_ms", "probability"
    )
    interval_cdf_x, interval_cdf = read_columns(
        Path(f"{prefix}-interval-cdf.csv"), "send_interval_ms", "cdf"
    )

    fig, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
    plots = (
        (axes[0, 0], size_x, size_pdf, "Packet-size PMF", "IP packet size (bytes)", "Probability"),
        (axes[0, 1], size_cdf_x, size_cdf, "Packet-size CDF", "IP packet size (bytes)", "CDF"),
        (axes[1, 0], interval_x, interval_pdf, "Inter-arrival PMF", "Inter-arrival time (ms)", "Probability"),
        (axes[1, 1], interval_cdf_x, interval_cdf, "Inter-arrival CDF", "Inter-arrival time (ms)", "CDF"),
    )
    for axis, x_values, y_values, title, xlabel, ylabel in plots:
        if ylabel == "CDF":
            padding = max(0.05 * (max(x_values) - min(x_values)), 0.5)
            plot_x = [x_values[0] - padding, *x_values, x_values[-1] + padding]
            plot_y = [0.0, *y_values, y_values[-1]]
            axis.step(plot_x, plot_y, where="post")
            axis.scatter(x_values, y_values)
        else:
            axis.stem(x_values, y_values, basefmt=" ")
        axis.set(title=title, xlabel=xlabel, ylabel=ylabel, ylim=(0, 1.08))
        axis.grid(True, alpha=0.3)

    output = Path(f"{prefix}-distributions.png")
    fig.suptitle("3GPP XR Pose Uplink Traffic Verification")
    fig.savefig(output, dpi=180)
    plt.close(fig)
    print(output)

    packets = read_packet_rows(Path(f"{prefix}-packets.csv"))
    send_times = [float(row["send_time_ms"]) for row in packets]
    delays = [float(row["delay_ms"]) for row in packets]
    ip_sizes = [int(row["ip_bytes"]) for row in packets]

    evidence_fig, evidence_axes = plt.subplots(
        1, 3, figsize=(15, 4.5), constrained_layout=True
    )

    # Evidence 1: transmission timeline. Equal tick spacing means a fixed 10 ms IAT.
    first_packets = min(20, len(send_times))
    relative_send_times = [
        send_time - send_times[0] for send_time in send_times[:first_packets]
    ]
    timeline = evidence_axes[0]
    timeline.eventplot(relative_send_times, lineoffsets=1, linelengths=0.7)
    timeline.set(
        title=f"Transmission timeline (first {first_packets} packets)",
        xlabel="Time since first transmission (ms)",
        yticks=[],
        ylim=(0.5, 1.5),
    )
    timeline.text(
        0.5,
        0.12,
        "Each vertical tick is one packet; spacing = 10 ms",
        transform=timeline.transAxes,
        ha="center",
    )
    timeline.grid(True, axis="x", alpha=0.3)

    # Evidence 2: IP throughput in non-overlapping one-second bins.
    bin_bytes = {}
    for send_time, ip_size in zip(send_times, ip_sizes):
        second = int((send_time - send_times[0]) // 1000.0)
        bin_bytes[second] = bin_bytes.get(second, 0) + ip_size
    seconds = sorted(bin_bytes)
    throughput_kbps = [bin_bytes[second] * 8.0 / 1000.0 for second in seconds]
    throughput = evidence_axes[1]
    throughput.plot([second + 0.5 for second in seconds], throughput_kbps, marker="o", ms=3)
    throughput.set(
        title="IP throughput (1-second bins)",
        xlabel="Time since traffic start (s)",
        ylabel="Throughput (kbps)",
    )
    throughput.axhline(80.0, color="tab:red", linestyle="--", label="Expected: 80 kbps")
    throughput.legend()
    throughput.grid(True, alpha=0.3)

    # Evidence 3: empirical delay CDF, aggregated at each unique delay value.
    delay_counts = {}
    for delay in delays:
        delay_counts[delay] = delay_counts.get(delay, 0) + 1
    delay_values = sorted(delay_counts)
    cumulative = 0
    delay_cdf = []
    for delay in delay_values:
        cumulative += delay_counts[delay]
        delay_cdf.append(cumulative / len(delays))
    delay_plot_x = [0.0, *delay_values, 10.5]
    delay_plot_y = [0.0, *delay_cdf, delay_cdf[-1]]
    delay_axis = evidence_axes[2]
    delay_axis.step(delay_plot_x, delay_plot_y, where="post")
    delay_axis.scatter(delay_values, delay_cdf)
    delay_axis.axvline(10.0, color="tab:red", linestyle="--", label="Target: 10 ms")
    delay_axis.set(
        title="Uplink delay CDF",
        xlabel="One-way delay (ms)",
        ylabel="CDF",
        ylim=(0, 1.08),
    )
    delay_axis.legend()
    delay_axis.grid(True, alpha=0.3)

    evidence_output = Path(f"{prefix}-evidence.png")
    evidence_fig.suptitle("Evidence from the ns-3 Run")
    evidence_fig.savefig(evidence_output, dpi=180)
    plt.close(evidence_fig)
    print(evidence_output)


if __name__ == "__main__":
    main()
