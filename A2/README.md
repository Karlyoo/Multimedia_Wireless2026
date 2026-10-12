# A2 — ns-3 Setup & XR Pose Uplink

- [Study Note](study_note.md) — ns-3 version, platform, installation steps,
  traffic model, and what broke.
- [Source code + run command](study_note.md#4-source-code-and-reproduction) —
  [`scratch/xr-pose-uplink.cc`](scratch/xr-pose-uplink.cc) and
  [`scratch/plot-xr-pose-results.py`](scratch/plot-xr-pose-results.py).
- [Result from my own run](study_note.md#5-result-from-my-own-run) — 6,000
  packets sent and received, 0% loss, 1.0816 ms mean/max delay, 80 kbps,
  traces, plots, and PCAP captures.
- [Presentation slides](A2-xr-pose-ns3.pdf) — PDF version for viewing.
- [Editable presentation](A2-xr-pose-ns3.pptx) — PowerPoint source.

## Run in the ns-3 source tree

The files in this folder are a compact submission bundle, not a complete
ns-3 distribution. Copy the two files under `scratch/` into the `scratch/`
directory of an ns-3.44 tree, then run:

```bash
cd /path/to/ns-3-dev
CCACHE_DISABLE=1 ./ns3 build xr-pose-uplink
CCACHE_DISABLE=1 ./ns3 run xr-pose-uplink
python3 scratch/plot-xr-pose-results.py --prefix xr-pose-uplink
```

The verified development tree on the author's machine is
`/home/karl/projects/ns-3-dev`.
