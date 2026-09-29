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
