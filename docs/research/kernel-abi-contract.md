# Stock kernel ABI contract

## Scope and evidence boundary

This report recovers the software-facing contract around the stock `.26` XDMA
module and correlates it with the stock Sparrow consumer. It is static evidence.
No module was loaded and no device was accessed. The exact stock binary is the
authority for shipped kernel plumbing. The pinned Orange-Rigol source is a
distinct public comparison, not vendor ground truth and not proof of MHO984 FPGA
behavior.

The exact module is
`local/reversing/firmware-extracted/stock-0.26/firmware/driver/xdma.ko`, SHA-256
`83d5064ae48c495a64ae329007e3c87e0dbc0391979b4d5ce6c1f02509a4a6e7` and build
ID `27105347d6b1d314fdf40c1d05a1cc288f232f16`. It is an unstripped AArch64
relocatable ELF with debug information. Its module description reports Xilinx
XDMA reference driver version `2019.2.51`. All 21 stock `.ko` files were hashed;
only `xdma.ko` contains the XDMA device templates and XDMA operations described
below. No supplied module exposes a `dma_auklet` name. That absence does not show
that `/dev/dma_auklet` lacks a driver: it may be built into the kernel or named
differently.

The public comparison remains pinned at Orange-Rigol kernel revision
`d23adbd11626f12abaf4bc742e250204fe2b9f8a`. Its source names, global and local
function names, node templates, ioctl constants, diagnostic strings and major
control flow agree closely with the stock binary. This is strong structural
correspondence, but the available evidence does not prove that this checkout is
the exact source used to build the stock object.

## Character-device surface

The stock module contains these node templates:

| Node | Stock file operations | Contract |
| --- | --- | --- |
| `xdma%d_bypass` | open, release, read, write, mmap | Base bypass BAR mapping; its cdev has no DMA engine. |
| `xdma%d_c2h_%d` | open, release, llseek, read, write, async read/write, ioctl | C2H scatter-gather DMA engine. |
| `xdma%d_h2c_%d` | same SGDMA operations | H2C scatter-gather DMA engine. |
| `xdma%d_bypass_c2h_%d`, `xdma%d_bypass_h2c_%d` | bypass read/write/mmap family | Engine-specific descriptor bypass interfaces. |
| `xdma%d_control`, `xdma%d_user` | control read/write/mmap/ioctl family | Config and user BAR interfaces. |
| `xdma%d_events_%d`, `xdma%d_xvc` | event/XVC-specific operations | Interrupt event and XVC paths; not observed in the stock consumer inventory. |

The stock `bypass_fops` object is at module `.rodata+0xd68`. Its relocations bind
read to `char_bypass_read` (`.text+0xa570`), write to `char_bypass_write`
(`.text+0xa410`), mmap to `bridge_mmap` (`.text+0x84b8`), open to `char_open`
(`.text+0x79b8`) and release to `char_close` (`.text+0x7a30`). The public source
creates the base bypass cdev with a null engine. Both bypass read and write ask
`xcdev_check` for an engine, so base-node read/write reject that construction;
base-node mmap remains the relevant control interface. Engine-specific bypass
nodes are separate.

Stock Sparrow opens `/dev/xdma0_bypass` with flags `0x101002`
(`O_RDWR|O_SYNC`) and requests offset zero, 16 MiB, read/write, shared mapping.
It closes the fd and unmaps 16 MiB in `Dev_Close`. The stock module's
`bridge_mmap` does not promise 16 MiB: it calculates
`off = vm_pgoff << PAGE_SHIFT`, selects the cdev's PCI BAR, rejects a requested
extent larger than the BAR remainder with `-EINVAL`, applies noncached page
protection and I/O VMA flags, then calls `io_remap_pfn_range`; remap failure is
`-EAGAIN`. The mapping persists by normal VMA/file lifetime rules. The binary
does not define register values or side effects.

## Control and DMA ABI

The stock control ioctl dispatcher at `.text+0x8598` contains the AArch64 ioctl
numbers below, matching the pinned public layout:

| Request | Value | Payload and result |
| --- | ---: | --- |
| `XDMA_IOCINFO` | `0xc0287801` | 40-byte read/write `xdma_ioc_info`; input begins with magic `0x586c0c6c`; returns PCI IDs, engine/driver versions, feature ID and BDF. |
| `XDMA_IOCOFFLINE` | `0x00007802` | No payload; takes the XDMA device offline. |
| `XDMA_IOCONLINE` | `0x00007803` | No payload; takes it online. |

It rejects the wrong ioctl type or number and bad user access with the paths
corresponding to `-ENOTTY` and `-EFAULT`; INFO also rejects a bad base magic.
Offline/online expose driver lifecycle operations, not FPGA reset semantics.

The SGDMA dispatcher at `.text+0x8d40` implements the public `q` ioctl family:
performance start/stop/get (`0x40087101`, `0x40087102`, `0x80087103`) and
address-mode set/get plus alignment get (`0x40047104`, `0x80047105`,
`0x80047106`). The performance requests encode an eight-byte pointer in the
ioctl number; the pointed record is 40 bytes: version, transfer size, stopped,
iterations, and three 64-bit counters. Version 1 is accepted. Address mode is
memory/incrementing `0` or fixed/non-incrementing `1`.

Synchronous SGDMA read/write uses the file position as the endpoint byte
address, checks direction, pins/maps the caller's pages into a scatter-gather
list, submits through `xdma_xfer_submit`, waits with the configured timeout and
unmaps the pages. Alignment is capability-dependent. For fixed/non-incrementing
mode, host buffer and endpoint must meet `addr_align`, and length must meet
`len_granularity`. In incrementing mode the host-buffer and endpoint low bits
must match. Therefore no fixed alignment value follows from the software alone.
The file operations also expose asynchronous vector I/O and completion callback
plumbing. This establishes availability, not stock application use or completion
timing.

The driver open path enables PCI, negotiates DMA masks, maps discovered BARs,
probes H2C/C2H engines and configures interrupt handling. BAR role, engine count,
alignment, granularity, stream versus memory mode and interrupt behavior are
runtime-discovered properties.

## Stock userspace correlation

The pinned stock APK and native library contain exactly three relevant paths:
`/dev/xdma0_bypass`, `/dev/xdma0_c2h_0` and `/dev/dma_auklet`.

* `Dev_PCIeInit` at ELF `0x27017c` opens the bypass node and requests the mapping
  above. `Dev_ReadRegister`/`Dev_WriteRegister` use 32-bit loads/stores at mapped
  byte offsets; `Dev_WriteAfgRegister` has a 64-bit store. These widths come from
  userspace instructions, not the kernel mmap callback.
* `DevAnalyzeTrace_Read` at `0x270634` reads `/dev/xdma0_c2h_0`. That is consistent
  with the module's C2H SGDMA read path, but static evidence does not establish
  endpoint position, returned framing, sample content, blocking duration or
  completion source for a particular call.
* `DrvDMA_Init` at `0x37de94` opens `/dev/dma_auklet`, maps 256 MiB shared and
  read/write at offset zero, and defines its destination pointer as mapping plus
  128 MiB. `DrvDMA_Copy` at `0x37dfc8` sends request `0x80086165` with a pointer
  to its first integer argument, then `0x80086163` with a pointer to a 32-bit
  status initialized to zero. Success is based on the second ioctl returning
  zero. No exact supplied module or pinned public driver source implements this
  path, so its request names, kernel payload interpretation, ownership,
  coherency, transfer direction and completion behavior remain unresolved.

## Limits and next evidence

Kernel plumbing does not establish FPGA reset values, register meanings,
readiness transitions, posted-write completion, memory ordering at the endpoint,
DMA payloads, acquisition framing, IRQ timing or calibration effects. The public
source cannot fill those gaps. Dynamic selection evidence is still needed for
actual BAR sizes and roles, engine capabilities and the `/dev/dma_auklet`
provider. Behavioral evidence is needed for every register and data-plane claim.

Raw disassembly, symbol tables, searches and hashes are under
`out/static-contract/kernel/`. Their manifest excludes itself from its digest
set. The typed companion record is
`experiments/static-contract/kernel-abi.toml`.
