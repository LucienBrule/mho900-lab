# Bounded observation of cached identity data

The next missing specimen input is the initialized stock identity/key context. The completed
[individual-option guest experiment](individual-option-catalog.md) uses coherent synthetic values; it cannot
establish the physical unit's cached DNA or derived file keys. This control prepares an observation method
without contacting the specimen.

## Read contract

The unchanged Auklet input is pinned to SHA-256
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`.
The reader accepts exactly two cached data objects:

| Object | ELF virtual address | File offset | Bytes per sample |
| --- | ---: | ---: | ---: |
| Cached DNA | `0xbbccf0` | `0xbbbcf0` | 8 |
| Derived file keys | `0xbbcd1c` | `0xbbbd1c` | 16 |

The source ranges are separate. Each sample contains eight bytes followed by sixteen bytes; no intervening
memory is requested by the external reader. Its two samples transfer at most 48 bytes of target memory.
Their equality is a repeated observation, not an atomic snapshot guarantee. The separate instrumented
guest setup reads code and identity state to prepare and verify the control; those setup reads are not
part of the proposed physical observation.

Both objects reside in file-backed `.data` inside the writable PT_LOAD segment. That segment starts at
virtual address `0xb69c00` and file offset `0xb68c00`. Consequently, deriving the load bias from a writable
map as merely `start - file_offset` would be wrong by `0x1000`. The reader must reconcile program headers
with executable and data mappings, including any read-only relocation split, and prove both live ranges
belong to the exact regular library file in readable private non-executable mappings.

One read-only `/proc/PID/mem` descriptor supplies positioned reads. There is no attachment, signal stop,
write to target memory, target function call or alternate backend. Process identity, boot/starttime,
relevant maps and backing-file identity are checked around the samples. Permission denial, a short read,
changed metadata or unequal samples ends the attempt.

Upstream Linux 3.18 stores an address-space reference in the opened memory file and applies access checks
when opening it. Reads use that stored reference, which avoids retargeting the descriptor merely because
a numeric PID is later reused. It does not pin every mapping or guarantee the process remains alive.
This is [upstream reference behavior][linux-proc], not an independently verified statement about every
change in the physical instrument's kernel.

## Disposable control

Setup uses the existing isolated API-25 ART host and original JNI/factory, then supplies the declared
synthetic DNA response and invokes the original key derivation. It records a comparison witness before
unloading and detaching its setup instrumentation. The separate reader then derives addresses from its
own ELF/maps evidence and reads the still-running process without invoking its methods.

Host-only addressing controls cover the virtual/file-offset difference, split mappings, inconsistent bias
and unsuitable mappings. Guest negative controls must reject wrong identity/pin/range requests before
any target-memory read. The positive arm must match both prior setup values and its independently derived
load bias, preserve health, and make no policy change during observation.

Existing guest instrumentation can affect the disposable guest's policy during setup. A reader pass under
that state proves addressing and data capture, not permission on the physical instrument. License service
initialization, installation and hardware-facing initialization are unnecessary for this control.

## Physical boundary

No specimen process lookup, network connection, helper staging or process-memory read is part of this
batch. A later proposal must identify the frozen helper, existing credentials, exact process and file
checks, maximum read extent and stop conditions. Temporary helper staging is a device-side filesystem
write and must be included explicitly in any later authorization; it is not made write-free by the
read-only nature of target-memory access.

The eventual question is whether the cached physical values agree with stock derivation and the copied
Key.data when evaluated offline. It does not establish full private-store contents, current trial state,
physical feature operation or a valid entitlement mutation procedure by itself.

[linux-proc]: https://github.com/torvalds/linux/blob/v3.18/fs/proc/base.c#L566-L659

## First control: mapping rejection before reading

Run `out/specimen-entitlement/cached-identity-reader-01` ran from 07:47:24 to 07:47:40 UTC on
2026-09-29. Stock setup completed with 49 factory services and 156 contiguous, exactly delivered journal
records. Setup was unloaded and detached before all four reader commands. No License initialization or
hardware-facing initialization occurred.

The wrong-pin and stale-starttime controls rejected at their intended gates. The invalid-range and positive
arms both rejected at `target-ranges`, before opening process memory or requesting any memory bytes.
The invalid-range guest control is confounded by the same mapping defect; its isolated rejection is
established by host controls, not this guest run.

Nine library map rows, spanning ten original executable pages, remained `rwxp` after instrumentation
unloaded. The two requested data ranges were still correctly file-backed and `rw-p`. The reader deliberately
rejects writable executable mappings anywhere in the pinned library. An independent resolver reproduces
the rejection; normalizing only those recorded code permissions in an in-memory analysis resolves the
expected addresses. This does not establish whether code bytes also differed.

The unchanged setup policy, final enforcing state, stable system-server PID and empty crash log were
preserved. The failure occurred before the after-read snapshot, so this run cannot establish a complete
post-read policy comparison or sample stability. Aggregate controller success flags are false; the ordered
journal, rather than those flags, establishes completed detach and the three negative-arm rejections.

| Artifact, relative to the run | SHA-256 |
| --- | --- |
| `result.toml` | `b35ab888dc5c1515942a16c404a4d489645bc7099ab0bad08b7cfcf919b5397a` |
| `evidence-sha256.txt` | `a14d870b1f0dcd6ed1abbd6a99cb1fa12c933c3089106ebee1204065886e8b30` |
| `reader/positive/manifest.toml` | `b793c7d2fd7e68bcfedc3ff78c454319bc4b17990177168562485bb36e6b3af9` |

The selected continuation is a setup-only restoration control. Capture the original library code mappings
and bytes before installing hooks; remove owned hooks, verify byte restoration, and restore only their
original executable-page permissions before detaching. Keep the compiled reader and its strict checks
unchanged. This is a new bounded hypothesis, not a reinterpretation of the failed run as a pass.

## Setup-restoration control

The admitted successor captures the original full executable mapping and library map geometry immediately
after stock JNI readiness, before any Auklet observer or synthetic response is installed. Once the final
stock call returns, setup removes its observers and response replacement, verifies all original executable
bytes, and restores only changed originally executable pages to their captured read/execute permissions.
It must prove the complete library mapping geometry and permissions match the baseline before ready, unload
and detach. Raw before/after code and mapping evidence remains local. The external reader binary remains
`2888a679e2884af821b920ee73ff399f578743d5672d81e1bc4a0aabe7b20bd4`.

These operations are cleanup of explicitly instrumented disposable setup. They are not proposed for the
physical process. A physical observation would use the existing uninstrumented mappings and fail if they
do not satisfy the reader contract.

Run `cached-identity-reader-02` (2026-09-29, 11:10:28–11:10:49 UTC) preserved the original RX bytes and
mapping baseline, completed stock identity setup, and removed fourteen owned listeners plus the DNA
replacement. Its next mapping check failed with `Unexpected setup library map alignment`. No external
reader command or protection-restoration operation ran. All 160 journal events were delivered exactly.
The setup's terminal failure exited its own process; later cleanup correctly found that process absent.

This failure does not prove which row violated the check: the implementation validated before preserving
the intermediate map text. The next bounded diagnostic must retain that raw text before parsing. No mapping
predicate, reader binary, policy or credentials will change merely to advance the experiment.

| Artifact, relative to `out/specimen-entitlement/cached-identity-reader-02` | SHA-256 |
| --- | --- |
| `result.toml` | `eceb66018903d79556746674c5ae10cc4ddf819bf1963266ef34f9c6619dad0c` |
| `evidence-sha256.txt` | `73670b18e914b2d6a9ef34b3d2f3af3a1dcac79ad5513cee7deba5166e10aa64` |
| `guest-events.jsonl` | `73a40b1b31cb06a28e5b207ac1526baf780950e7b7dab4095f4c0e6f96633ede` |

## Mapping diagnostic

Run `cached-identity-reader-03` preserved the rejected raw maps before parsing. The extra row is a separate
read-only private mapping of the same complete library file, offset zero, length `0xbe1000`, below the
actual loaded module. It is a file view rather than a PT_LOAD mapping at the module's load bias. Its
creator is not established by this observation. The original guard conflated every same-file mapping with
the loaded module. It rejected before protection restoration or external reading; this run is diagnostic,
not a reader pass. Raw text and the exact rejected row are retained under `reader/setup-restoration/`.

A valid successor may distinguish one complete read-only private file view, disjoint from the complete
loaded-module extent, while retaining exact identity, loaded-segment geometry, permission and stability
checks. Partial, writable, shared, executable, overlapping or ambiguous views must still fail. This needs a
new reader build and explicit controls; the original build06 rejection remains correct for its contract.

## Detached read established; original verifier failure retained

Run `cached-identity-reader-04` (2026-09-29, 11:16:54–11:17:12 UTC) used build07, SHA-256
`de5c56e497e786d45776ece8dab386184ea32e67f4b9e0b0990a0a9fcb8c57fc`. Host Python and compiled C controls
accept the exact disjoint read-only file view and reject writable, shared, executable, partial, overlapping
and duplicate alternatives. The unique loaded-module anchor and cached-data checks remain mandatory.

The control restored all 11,964,416 original executable bytes and ten original executable-page permissions,
then unloaded and detached setup. All 180 journal records matched delivery. The three negative reader cases
rejected before memory access. The positive reader made exactly four positioned reads of 8, 16, 8 and 16
bytes through one read-only descriptor. Both 24-byte samples matched each other and the prior setup witness.
Process identity, backing-file identity, relevant mappings and guest policy remained stable through reading.
No target method, attachment or target write occurred during external observation. The restored setup code
and its separate data preparation are not part of the proposed physical observation.

The controller succeeded, but the run's frozen final verifier incorrectly retained build06's binary/source
pin. Consequently the original `result.toml` remains `runner_exit = 1`, stopped at verification. It has not
been rewritten. A separately preserved offline audit changes those two pins to the admitted build07 and
validates the existing artifacts without another guest run. That audit accepted restoration, addressing,
negative cases, samples, identity, policy and build provenance. The root's 65 artifact hashes and all 75
reader artifact hashes were also checked.

| Artifact | SHA-256 |
| --- | --- |
| Run `result.toml` | `9fb25ec6a59d9262031d71af5ce675dda3608b97fd18fb5ebb4b68827bb17106` |
| Run `evidence-sha256.txt` | `d8737eee2432cbdb8e835a13095c0fda6db79d2170ff8994a330921f6d4de74c` |
| Run `reader/positive/manifest.toml` | `85065e0c13bf5c244577f5e99a8a67e9a81edae51482bb5b392040c6ad3ee456` |
| `out/overnight/cached-reader-04-audit/verifier.py` | `8730784f02aa0645edea5716c6cdcdab90d0f60c75a68a340b0e4a9674361ec2` |
| `out/overnight/cached-reader-04-audit/result.toml` | `7859a6df21682cdeb6aee43433da81b8b51eb6715699fcdaa2e9b5ed12d5909e` |

## Decision and proposed bench question

The guest establishes a bounded, independently addressed observation method. It does not establish that the
physical kernel permits it, that physical cached values match this synthetic fixture, or that repeated
samples form an atomic snapshot. No further synthetic permutations can settle those questions.

The next proposed action, requiring renewed authorization, is one observation of the already initialized
physical process's cached DNA and file keys. Reconfirm the isolated capture path and process identity;
stage the frozen build07 helper in an explicitly approved temporary location; verify its bytes and the
stock library; use existing credentials; read the two ranges twice; preserve metadata and raw samples;
then stop. Staging and output creation are device-side filesystem writes and belong explicitly in that
request. Do not rerun identity initialization, access mapped registers, attach instrumentation, restart ADB,
change policy or fall back to a different memory interface. Permission denial is a result, not permission
to escalate.

Offline comparison can then ask whether original stock derivation reproduces the physical cached file keys
and coherently decodes the already acquired Key.data. Initialized private/FRAM state, actual option-query
semantics on the specimen, physical installation durability and feature operation remain separate questions.
Reporting is the selected next task; no physical action is admitted by this decision.

## Authorized physical observation: standalone-file precondition stopped

The subsequent [physical observation](physical-cached-identity-observation.md) reached existing ADB
credentials and preserved Sparrow maps, then stopped before staging or executing the reader. The physical
process maps the installed APK directly; the previously acquired APK places uncompressed Auklet at offset
`0xf05000`, consistent with the observed executable mapping. The standalone-file reader contract therefore
needs an offline APK-entry mapping control before another physical proposal. No physical cached values or
process-memory permissions were established. Capture and host restoration passed; operator-reported cable
reconnection has unknown timing relative to the captured DHCP exchange. This supersedes the outstanding
standalone-reader proposal without turning its negative result into a successful read.
