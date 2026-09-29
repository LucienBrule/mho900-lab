# Physical D-capability startup and persistence

Independent offline verification accepted the physical deployment and a separate
normal reboot without another native-file or license write. Both selected the
derived D-capability policy while
retaining the signed stock Sparrow APK and public MHO984 identity. The retained
postboot process maps identify the standalone derived native library; the bounded
reader returned raw and effective bandwidth enums 18/18 in both samples. All ten
ordinary option statuses remained enabled, with BND false. This is a software
capability result, not a measurement of 1 GHz analog performance.

Stage 4 is complete for software capability selection and reboot persistence.
Stage 5 remains RF evaluation; no analog bandwidth result is claimed.

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

Neither enum 18 nor a normal UI establishes analog bandwidth, calibration
accuracy, feature operation or acquisition quality. The next evaluation is the
[RF comparison plan](rf-performance-evaluation-plan.md).

The complete run contains 395 sealed artifacts; SHA-256 of `artifacts.toml`:
`d30a25d29ec889aee369645f966d24dd8cc214237af3d2f1081ee52e39d04fa2`.


## Independent persistence reboot

The second run, `out/physical/mho984-d-persistence-20260929T181408Z`, requested one
normal reboot at 18:14:40.520 UTC. The client again timed out after ten seconds;
wire reconstruction proves one request, peer TCP acknowledgment and ADB OKAY,
without retransmission. A fresh isolated lease was acknowledged at
18:15:19.544 UTC. The new boot loaded the same derived native file. No native
file, package or entitlement was installed or rewritten in this run.

All three status checkpoints returned the unchanged public identity, ten enabled
ordinary options and BND false. The fixed observer independently resolved the
standalone ELF mappings and read repeated raw/effective 18/18 in 16 bytes total.
The signed APK, ten license files, key and vendor bytes were unchanged. The only
logical deltas were the same validated bandwidth-header rewrite and randomized
identity fallback cache; all 320 calibration payload bytes remained identical.
Postboot and post60 archives were byte-identical, and process identity was stable.

The pre-reboot screenshot shows the normal UI still present several minutes
after the first deployment observation. The second early postboot image again
shows the startup spinner; its later image shows the normal waveform UI with
AUTO/RUN and no prompt. These are sampled UI observations, not a continuous
video or proof that the early spinner interval was normal full-UI operation.

The second capture contains 254,911 complete frames, zero reported kernel drops,
and recorder exit 0. Its SHA-256 is
`6d33974150ec45caeaa0d24eb4d1346c6764c880404acfbfde66141315d1d8df`.
The complete run contains 370 sealed artifacts; SHA-256 of `artifacts.toml`:
`42cc6a5277bb8adb15bad73d85c505a279afb2b913589256b20c512efa239727`.
The final independent verifier passed without further source changes.

Both runs removed the temporary host address and stopped their lease helper and
capture. Host network preference files were byte-identical before and after.
Forwarding and sharing remained disabled and the default route stayed separate.
The physical guest's pre-existing SELinux state was Disabled and remained so;
this is distinct from the Enforcing disposable-guest controls.

## Current state and rollback boundary

The instrument is left running with the derived native file selected, public
MHO984 identity retained, and all ten ordinary options enabled. The original
signed APK remains in place. Stock originals and the acquired baseline remain
preserved; no claim is made that a raw live-storage backup is an atomic snapshot.

The rollback mechanism is removal of only the recorded introduced native file
followed by a normal reboot, then proof of original APK-backed stock Auklet,
17/17 policy, unchanged identity/options and normal UI. This mechanism passed in
the disposable loader control; physical rollback has not been exercised because
both physical D boots succeeded. Any future rollback must first revalidate the
actual package path, introduced-file hash, capture and lease, and record its own
result. Failed connectivity or capture is not permission for an unobserved write.
No RF input, probe, USB, calibration, factory reset or host-policy change was used.
