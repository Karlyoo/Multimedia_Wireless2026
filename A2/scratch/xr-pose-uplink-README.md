# A2 — ns-3 Setup and XR Pose Traffic Model

## Environment

- ns-3 version: 3.44
- Platform used for the verified run: Ubuntu 22.04.5 LTS, x86-64
- Source model: 3GPP TR 26.926, clause 5.9.2 (Pose Uplink Model)

The model uses a fixed pose. Clause 5.9.2 specifies pose sampling and traffic
generation; movement is not needed to validate the traffic model.

## Model

| Item | Setting |
|---|---:|
| Nodes | One XR device, one server |
| Transport | UDP/IPv4 |
| Pose sample interval | 1 ms (1 kHz) |
| Report interval | 10 ms (100 Hz) |
| Pose data sent | Latest sample |
| Pose | Fixed position `(1,1,1.2)`, quaternion `(0,0,0,1)` |
| Packet | 60-byte pose + 12-byte report header + UDP 8 + IPv4 20 = 100 bytes |
| Link | Point-to-Point, 10 Mbps, 1 ms one-way propagation |
| Duration | 60 s (6,000 packets) |

The 60-byte pose contains three `float32` position values, four `float32`
quaternion values, a `uint64` sample timestamp, a `uint32` device ID, and 20
reserved bytes. Each 1 ms sample updates the timestamp. Every tenth sample is
sent immediately, which guarantees that sampling occurs before reporting.

## Build and run

```bash
./ns3 build xr-pose-uplink
./ns3 run xr-pose-uplink
python3 scratch/plot-xr-pose-results.py --prefix xr-pose-uplink
```

If ccache cannot write its configuration or temporary directory in a restricted
environment, build with:

```bash
CCACHE_DISABLE=1 ./ns3 build xr-pose-uplink
```

## Verified baseline result

| Metric | Result |
|---|---:|
| Sent / received | 6,000 / 6,000 |
| Loss rate | 0% |
| Mean / maximum uplink delay | 1.0816 / 1.0816 ms |
| Delay no greater than 10 ms | 100% |
| Mean pose age at reception | 1.0816 ms |
| IP-layer offered traffic | 80 kbps |
| Packet-size distribution | P(100 bytes) = 1 |
| Inter-arrival distribution | P(10 ms) = 1 |

The 1.0816 ms delay is 1 ms propagation plus serialization of the 100-byte IP
packet and 2-byte PPP header on a 10 Mbps link. Wireshark therefore displays a
102-byte PPP frame containing a 100-byte IPv4 packet and a 72-byte UDP payload.

Generated files include the per-packet trace, summary, packet-size and
inter-arrival PDF/CDF CSV files, `xr-pose-uplink-distributions.png`,
`xr-pose-uplink-evidence.png`, and PCAPs for both link endpoints.
