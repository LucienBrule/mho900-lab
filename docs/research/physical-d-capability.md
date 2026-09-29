# First physical D-capability startup

Independent offline verification accepted the first physical deployment. It selected the derived D-capability policy while
retaining the signed stock Sparrow APK and public MHO984 identity. The retained
postboot process maps identify the standalone derived native library; the bounded
reader returned raw and effective bandwidth enums 18/18 in both samples. All ten
ordinary option statuses remained enabled, with BND false. This is a software
capability result, not a measurement of 1 GHz analog performance.

The independent persistence reboot is still pending. This report covers only
the deployment boot and its retained observations.

The deployment follows the [disposable native-loader control](native-library-deployment-control.md)
and [complete acquired-catalog capability comparison](acquired-combined-capability.md).
The native file has SHA-256
`09689a442e8d285775b37089a8d631e1e445fe03d3499e830cdcc8f32439504e`.
It differs from the stock embedded ancestor in 27 bytes within the 32-byte span
at file offset `0x42949c`. The original APK remains byte-identical, SHA-256
`6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b`;
there was no APK replacement or resigning.

Current package metadata selected the native-library directory. The destination
was absent before transfer. A temporary file was transferred, read back and
hashed, assigned system ownership and mode 0644, then renamed into that directory.
The postboot and later snapshots retained the same derived bytes and standalone
mapping. The APK still supplies legitimate executable mappings for `libc++_shared.so`
and `libfftw3f.so`; the excluded duplicate is specifically the embedded stock
Auklet executable segment. This extends the loader-control result to the actual stock application;
it does not imply that arbitrary package layouts would behave identically.

| Observation | Retained result |
|---|---|
| Normal reboot request | One request at 18:08:02.322 UTC on 2026-09-29 |
| Client transport | Timed out at 18:08:12.364 UTC; request was not retransmitted |
| Reboot wire evidence | Exactly one ADB reboot OPEN, acknowledged by peer TCP and matching ADB OKAY |
| Bounded readiness | Fresh isolated DHCP ACK and changed boot identity; readiness window closed at 18:08:45.926 UTC |
| Early postboot screenshot | RIGOL logo and spinner despite resumed-activity metadata |
| Later screenshot | Normal waveform UI, AUTO/RUN, no modal prompt visible |
| Native policy observation | Four fixed 4-byte reads, 16 bytes total; repeated 18/18 |
| Ordinary options | Ten enabled, BND false; no entitlement installation in this run |
| Capture | 268,121 complete retained frames; zero reported kernel drops; recorder exit 0 |

The early screenshot at approximately 18:08:53 UTC and the later screenshot at
approximately 18:09:55 UTC delimit a UI transition rather than sixty seconds of
proven full-UI stability. Process identity remained stable across the interval.
A resumed Android activity alone does not establish that Sparrow has finished
its own startup screen. The later screenshot establishes that the full waveform
UI had appeared; no control interaction or RF measurement was used to assess it.

The ten saved license files, key file and vendor file remained byte-identical.
The logical file set was unchanged. The only changed logical files were the two
startup-written files already examined in the
[ordinary boot data reconciliation](ordinary-boot-data-reconciliation.md):

- `data/cal_afe_bandwidth.hex`: the 320-byte coefficient payload was unchanged;
  only the established header CRC/time words may differ, with both CRCs valid.
- `data/cal_tmp_hex.log`: the 172-byte randomized identity fallback cache changed.
  Its retained size and known producer explain the permitted difference, but do
  not independently authenticate its decoded contents.

The postboot and later logical archives matched each other exactly. All other
captured logical-file bytes remained unchanged. No calibration, reset, new
ordinary entitlement or unrelated configuration operation was requested by this
controller.

Independent verification is implemented in
[`verify-d-capability.py`](../../tools/bench/verify-d-capability.py). It checks the
sealed predecessor, raw SCPI TCP transcripts, reboot request delivery, exact
native transformation and file ownership, standalone ELF/map geometry, process
and boot epochs, repeated samples, logical preservation, capture statistics and
host restoration. UI images require a separate visual reading; the verifier
does not promote resumed-activity metadata into a claim of a normal visible UI.
Three offline verifier attempts initially rejected the retained run because of
verifier assumptions: a leading package-section delimiter, an overly broad
exclusion of executable APK mappings, and SYN-only reconnect attempts without
server responses. The fixes were checked against actual retained metadata and
wire evidence. The final verifier permits the two legitimate APK native members,
rejects stock Auklet segment overlap, and separately counts nine transports with
no payload in either direction. Every payload-bearing ADB transport still
requires complete, consistent reassembly. Full-verifier tamper controls reject
an extra reboot request and a borrowed stock Auklet mapping. All three original
verifier failures are preserved; no physical rerun was needed.

Private evidence resides under
`out/physical/mho984-d-deploy-20260929T180636Z/`. Its pcap SHA-256 is
`ef36a910830d8c4eb088e68525d2fd8d2fba328364b7dd6b4e1a7caafec645d9`.
The accepted independent audit is retained separately under
`out/overnight/d-deployment-independent-audit/accepted-04.toml` and the sealed
run's `independent-validation.toml`.

The next separate checkpoint is another normal reboot without rewriting the
native file or licenses, followed by the same identity, option, mapping, policy,
file-preservation and UI observations. RF transfer-function measurements belong
to the later RF evaluation stage. Neither enum 18 nor a normal UI establishes
analog bandwidth, calibration accuracy, feature operation or acquisition quality.

The complete run contains 395 sealed artifacts; SHA-256 of `artifacts.toml`:
`d30a25d29ec889aee369645f966d24dd8cc214237af3d2f1081ee52e39d04fa2`.
