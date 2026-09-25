# XDMA reference comparison and modeling boundary

## Decision before implementation

Use the pinned Orange-Rigol kernel as an ABI reference. Start with a narrowly
scoped userspace adapter at the stock device-open/mapping boundary, retaining
the stock register-access instructions and trapping their actual memory accesses.
The first batch supplies mapping transport only, then stops on the first unknown
register access. It supplies no successful register read, completion, DMA payload,
model identity, or waveform.

This selects direction 2, with process instrumentation as the initial transport.
It is a hypothesis about an observable boundary, not a claim of a complete faithful
XDMA device. Production reuse of kernel code remains an option once evidence
requires DMA or kernel semantics that this adapter cannot preserve.

**Batch result:** the public-source comparison supports this narrow logical
boundary, but the initial Frida adapter failed reliable live-access capture.
Private controls passed; neither final fresh run produced a complete unsupported
access record. No register behavior was supplied. See the evaluation below before
using the prototype.

## Reference provenance

The [kernel repository][kernel] is pinned at
`d23adbd11626f12abaf4bc742e250204fe2b9f8a`; current upstream `main` matched this
revision when inspected. Its README reports an OrangePiRK3399-derived kernel and
DHO924S testing. Neither statement validates MHO984 behavior.

The XDMA path history records import commit
`8585c26df087c4e4c419b9ebf1edae8b48646c85`, described as an import from Xilinx.
The inspected files carry Xilinx GPL-2.0 headers and version macros `2019.2.51`.
Treat this as code present in the public reverse-engineering project, not as
evidence that all its XDMA internals were reconstructed from Rigol hardware.
No assertion of equality with an upstream Xilinx release or the vendor kernel
module is made.

`experiments/xdma-boundary/reference.toml` pins every inspected file by SHA-256
and Git blob ID, plus raw GitHub API responses. `xdma/libxdma.c` and `.h` are
symlink contents in the Git tree; the referenced `libxdma/` implementation is
downloaded and pinned separately. External source stays under ignored
`local/reference/`; proprietary binaries are not copied into source.

## What each side establishes

| Contract element | Stock consumer evidence | Public reference evidence |
| --- | --- | --- |
| Device open | Live JNI wait; static bypass path, flags `0x101002`. | `xdma_cdev.c` names the base bypass node. |
| Mapping | Offset 0, 16 MiB, `PROT_READ|PROT_WRITE`, `MAP_SHARED`. | `bridge_mmap` exposes a selected PCI BAR. |
| Register writes | `Dev_WriteRegister`: 32-bit store at base + offset. | BAR mapping passes CPU writes to hardware. |
| Register reads | `Dev_ReadRegister`: 32-bit load at base + byte offset. | No callback defines register read values. |
| Wider write | `Dev_WriteAfgRegister` stores 64 bits. | Mapping does not prescribe access width or meaning. |
| Acquisition stream | Static `DevAnalyzeTrace_Read` calls `read` on C2H. | SGDMA read submits an engine transfer. |
| Other DMA | Stock `/dev/dma_auklet` map/ioctl path exists. | This XDMA implementation does not define that ABI. |

Stock register accessor observations are fresh disassembly at `0x2703c8`,
`0x270594` and `0x2704fc`. `Dev_WriteWaveDataRegister` computes a scaled address
but the inspected function contains no data store; its name alone is not a
behavior specification. Acquisition and wider accesses are static leads, not
claims that startup already executed them.

The pinned source gives useful concrete distinctions:

- `cdev_bypass.c` binds open/release/read/write/mmap, but read/write require an
  engine. `xdma_cdev.c` creates the base bypass device with a null engine, so those
  base-node calls encounter the engine check and return `-EINVAL` in this source.
  The engine-specific bypass nodes are different interfaces. Do not interpret
  base bypass read/write as a generic register protocol.
- `cdev_ctrl.c:192` computes the physical BAR address plus page offset, checks the
  requested extent against the resource remainder, selects noncached protection,
  sets VMA flags and uses `io_remap_pfn_range`. It returns `-EINVAL` for an oversized
  request and `-EAGAIN` when remapping fails. It does not specify a fixed 16 MiB BAR.
- `libxdma.c:1800` identifies user/config/bypass BARs by discovered layout. Its
  device-open path enables PCI, maps BARs, establishes DMA masks, probes engines,
  and configures interrupts. These are physical-backend requirements.
- `cdev_sgdma.c` uses file position as endpoint address and validates alignment
  against engine capabilities before submitting transfers. Those capabilities and
  stream contents cannot be inferred from the existence of the C2H node.

This reconstructs transport, naming, lifetime checks and DMA plumbing. It does
not reconstruct the Rigol acquisition register map, reset values, busy/ready
transitions, sample timing, side effects, interrupts or calibration behavior.
The stock userspace remains authoritative about requests; physical observations
will eventually be needed to validate modeled responses.

## Alternatives and fidelity limits

| Direction | Assessment |
| --- | --- |
| Reuse the entire driver now | Requires synthetic PCI, BAR discovery, DMA engines and IRQs before app evidence. |
| Small mapped-access adapter | Keeps actual load/store instructions; exposes offset, width, value and call site. |
| Replace `Dev_Read/WriteRegister` | Can miss direct accesses and changes the executed instruction path. |
| Intercept JNI or higher API | Hides initialization and its failure behavior; too broad for the present question. |
| QEMU/device implementation | Strong MMIO isolation; larger platform investment before the register set is known. |

The selected experiment intercepts libc only in the exact installed stock process.
It binds the bypass open to its stock call site and flags, uses a real disposable
descriptor as transport, and accepts only the observed mapping tuple from the
stock mmap call site. The backing mapping is deliberately inaccessible anonymous
memory. The intended fault record reports the instruction, offset and registers, then stops;
it does not complete the unknown access. Original APK and native-library bytes
remain unchanged, including native accessor instructions.

This does **not** reproduce device cache attributes, memory ordering, shared
aliases across processes, PCI discovery, DMA coherency, IRQs or scheduling.
Those are explicit limits, not silently assumed equivalences. Normal RAM filled
with zeroes would let unknown reads appear successful and is therefore unsuitable.
Intercepting open/read/ioctl alone would leave mapped accesses unobserved.

The eventual model boundary should be ordered events containing operation,
device-relative byte offset, width, written value, thread and caller, plus an
explicit response or unsupported result. The same events can drive a deterministic
model or recorded replay; a physical backend would acquire comparable traces.
Future instruction emulation, concurrency, side-effect and ordering behavior
require separate contracts and tests. This batch does not implement them.

## Bounded hypothesis batch

Test whether the adapter can accept the stock mapping and stop on the first
unknown mapped access without returning invented hardware state. First exercise
the fault detector with known private read/write controls and an ordinary-memory
control. Then run two fresh guests, comparing normalized first-access evidence.
Preserve negative or unexpected outcomes and evaluate before extending the model.
No physical instrument, host security change or native-library patch is involved.

The mechanism uses Frida's [documented exception and memory APIs][frida]; their
behavior must be tested on the pinned 16.7.19 runtime. The APIs are a transport
choice, not a source of instrument semantics. Its mandatory injected JavaScript
bridge is the ecosystem exception to Kotlin-first tooling; verification is Kotlin.

## Preliminary harness observations

`mapping-01` passed the private access controls but admitted the device open before
the adapter-ready event, with no captured mmap request. Its event writes also
arrived out of sequence. The app faulted; `system_server` remained stable. This
run is excluded from validating the mapped-access hypothesis. Hook activation is
now gated until all hooks are installed, and evidence writes keep the JS lock.

`mapping-02` captured the exact stock mmap tuple and the inaccessible mapping,
then the app faulted at mapping base + `0x4048`. It did not capture a complete
access record and is likewise excluded from a successful observation claim.
The adapter retained an `onLeave` return-value wrapper, contrary to Frida's
documented lifetime rule. The correction copies the address value. These are
harness corrections, not changes to modeled register behavior. Original runs
and their source snapshots remain preserved.

## Final repeat and evaluation

The final runtime helpers are byte-identical between `mapping-03` and `mapping-04`.
Both used fresh guest data and passed four private 32/64-bit read/write fault
controls, an ordinary-memory control and three APK-admission rejection controls.
The installed stock APK and packaged native library retain their pinned hashes.

| Run | Recorded live outcome |
| --- | --- |
| `mapping-03` | Open returned fd 56; no mmap event; read fault at `0x4047`, with no adapter region. |
| `mapping-04` | Exact mmap tuple; protected 16 MiB region; Zygote reports app PID 2513 exited on signal 11. |

The first run does not establish whether the stock mmap call bypassed the hook,
failed, or encountered an instrumentation fault. The second does not establish
fault address, instruction, width, register value or device-relative offset.

The second run's crash buffer and tombstone directory are empty. Its event journal
ends at `mapping-ready`; its CLI exit code is zero despite the app dying. Neither
CLI success nor helper completion validates a capture. The synchronous guest
journal contains more events than the console and is the primary adapter record.
No complete `unsupported-mmio` record exists in either final run.

`system_server` retained PID 1051 across all three samples in `mapping-03`, and
PID 1068 in `mapping-04`. Both apps terminated and both guests were torn down.
Zygote maps show no Frida injection. The existing scoped admission and process
labeling fixtures remain necessary; Frida's guest SELinux policy changes remain
a fidelity limit, with enforcing mode retained. No host policy or instrument was
changed.

This is a repeat failure to establish reliable end-to-end observation, with
different failure stages. It is not a reproducible first-register trace or proof
that Frida cannot implement the boundary. The preliminary `mapping-02` address
difference, `0x4048`, is a candidate offset only: that run had a known harness
defect and no complete instruction witness. Do not use it to invent a register
name, reset value or response.

**Decision:** retain the mapped-access contract as the smallest justified model
boundary, reject this adapter as ready for behavioral modeling, and close this
batch as a negative experiment. The public driver still supplies transport
semantics rather than the missing register behavior. There is no evidence yet
that importing the PCI/DMA backend or replacing a higher native API would resolve
the actual observation failure with better fidelity.

The next bounded question is whether an independent observer can record the
stock mmap target, fd, arguments and return, followed by the first signal and
register state, outside this callback path. Static relocation inspection locates
the stock mmap GOT entry at ELF virtual address `0xb850f0`; runtime resolution is
unverified. A native syscall/fault supervisor is a candidate to evaluate, not a
validated implementation. Its first contract should prove deterministic capture
on private controls and the unchanged stock process before supplying any hardware
response. No successor behavioral model is admitted in this batch.

## Reproduction and evidence

`experiments/xdma-boundary/results.toml` pins source snapshots, raw evidence indexes
and verifier outputs. Raw logs may contain private machine information and remain
ignored; the tracked manifests use project-relative paths. Reference files can
be retrieved and checked with:

```sh
tools/guest/fetch-xdma-reference.sh
```

With the previously pinned guest inputs and `ANDROID_SDK_ROOT` configured locally,
a new disposable run uses a fresh identifier:

```sh
tools/guest/run-admission.sh mapping-new mapping
kotlin tools/guest/VerifyMapping.main.kts out/guest-admission/mapping-new capture
```

The default `capture` verifier must fail for this batch: it requires the missing
complete access witness and checks its opcode against the installed stock ELF.
The explicit `negative` mode checks the two recorded failure profiles without
promoting them to successful captures:

```sh
kotlin tools/guest/VerifyMapping.main.kts out/guest-admission/mapping-03 negative
kotlin tools/guest/VerifyMapping.main.kts out/guest-admission/mapping-04 negative
```

It verifies raw-file hashes, stock bytes and signers, UID and process label,
admission controls, event ordering, process death and server stability. A new
failure shape requires review rather than being accepted as a generic negative.
No further guest runs or register responses were added after the final repeat.

[kernel]: https://github.com/norbertkiszka/rigol-orangerigol-linux_4.4.179
[frida]: https://frida.re/docs/javascript-api/
