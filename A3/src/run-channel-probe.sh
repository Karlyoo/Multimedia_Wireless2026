#!/usr/bin/env bash
set -euo pipefail

# The source tree is already built separately. This compiles only our probe,
# without installing/copying source files into the user's ns-3 checkout.
probe_ns3_dir=${NS3_DIR:-/home/karl/projects/ns-3.48-nr}
probe_source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
probe_output_dir=${1:-"$probe_source_dir/../results/probe"}
if (( $# > 0 )); then shift; fi
mkdir -p -- "$probe_output_dir"
probe_output_dir=$(cd -- "$probe_output_dir" && pwd)
probe_build_dir=$(mktemp -d /tmp/a3-channel-probe.XXXXXX)
export MPLCONFIGDIR="$probe_build_dir/matplotlib"

g++-12 -std=c++23 -O2 -DNS3_ASSERT_ENABLE -DNS3_LOG_ENABLE \
    -I"$probe_ns3_dir/build/include" -I/usr/include/eigen3 \
    "$probe_source_dir/channel-spatial-probe.cc" \
    -L"$probe_ns3_dir/build/lib" -Wl,-rpath,"$probe_ns3_dir/build/lib" \
    -lns3.48-spectrum-default -lns3.48-propagation-default \
    -lns3.48-mobility-default -lns3.48-network-default \
    -lns3.48-antenna-default -lns3.48-core-default \
    -o "$probe_build_dir/channel-spatial-probe"

"$probe_build_dir/channel-spatial-probe" "$@" --output="$probe_output_dir/correlation.csv"
python3 "$probe_source_dir/check-channel-probe.py" "$probe_output_dir/correlation.csv" \
    --plot "$probe_output_dir/correlation.png"
