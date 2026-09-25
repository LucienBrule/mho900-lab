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
| Device open | Live JNI wait; static `/dev/xdma0_bypass`, flags `0x101002`. | `xdma_cdev.c` names the base bypass node. |
| Mapping | Offset 0, 16 MiB, `PROT_READ|PROT_WRITE`, `MAP_SHARED`. | `bridge_mmap` exposes a selected PCI BAR. |
| Register writes | `Dev_WriteRegister`: 32-bit store at base + byte offset. | BAR mapping passes CPU writes to hardware. |
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
| Reuse the entire driver now | Requires a synthetic PCI endpoint, BAR discovery, DMA engines and IRQs before app evidence. |
| Small mapped-access adapter | Preserves actual load/store instructions and exposes offset, width, value and call site. |
| Replace `Dev_Read/WriteRegister` | Convenient, but can miss direct accesses and changes the executed instruction path. |
| Intercept JNI or higher API | Hides initialization and its failure behavior; too broad for the present question. |
| QEMU/device implementation | Strong future MMIO isolation; larger platform investment before the reached register set is known. |

The selected experiment intercepts libc only in the exact installed stock process.
It binds the bypass open to its stock call site and flags, uses a real disposable
descriptor as transport, and accepts only the observed mapping tuple from the
stock mmap call site. The backing mapping is deliberately inaccessible anonymous
memory. A fault reports the actual instruction, offset and registers, then stops;
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

[kernel]: https://github.com/norbertkiszka/rigol-orangerigol-linux_4.4.179
[frida]: https://frida.re/docs/javascript-api/
