# Static initialization tail: versions, DDR and later subsystem boundaries

The stock run stopped at the first version read after 464 accepted stores. Static
recovery now describes the remaining `Drv_Init(bool)` parent flow through its return,
including the complete version/DAC/DDR/self-test region. The typed
[operation graph](../../experiments/init-tail/grammar.toml) preserves conditional edges,
read dependencies and explicit unknown callees. It is not an executable flat transcript
and does not claim complete transitive recovery of calibration or acquisition.

The pinned stock library remains the authority for software behavior. A Kotlin producer
binds reviewed annotations to function ranges, instruction words and relocations.
Independent byte/shape verification and a separate semantic review serve different
purposes: a valid graph and matching opcode do not themselves prove an annotation.
No guest was run and no device response was implemented during this static batch.

## Recovered region before calibration

| Operation | Software consequence | Unresolved input |
| --- | --- | --- |
| `R32(4)`, `R32(0)` | Pack `((R4 & 0xffffff) << 8) \| (R0 & 0xff)` | Returned version words |
| `R32(0x401c)` | Separate version value | Returned word; distinct from GPIO version |
| Version logging | Neither value nor read status controls this immediate path | Logging completion |
| `W32(0x1428)` | Low half `0x646e`; preserve live upper half | Writable DAC shadow |
| DDR config selection | Nonzero enables skip-tap reads and memory-reset write | Live series/config field |
| Five skip-tap reads | Mask values into six output locations; last output is zero | Returned words |
| `W32(0x1000)` | Clear bits 2 and 3, preserving other shadow bits | Live SPU control shadow |
| Self-test `R32(0x1008)` | Copy bit 29 of post-call object to completion byte | Returned state or retained object |
| Self-test `R32(0x1210)` | Clock-range predicate and raw value are logged | Returned counter word |
| Parent retry loop | Repeat the entire self-test until complete or retries exhausted | Completion sequence |
| Optional `W32(0x1008)` | Set bit 31 of the final self-test object | Final object value |
| Calibration call | Enter the next unrecovered subsystem | Filesystem/configuration and calibration behavior |

`SetDacPolling(5000000000, 5500000000)` uses unsigned division by `50000000`,
yielding `100` and `110`; those become the two low bytes `0x646e`. The full write
is `(live_dac & 0xffff0000) | 0x646e`. Image-zero BSS is not a substitute for a
live shadow observation.

The DDR selector comes from the selected series record's configuration pointer at
`+0x18`, then the integer at configuration `+0x68`. The MHO900 configuration image
contains `1`, but this is writable state. Zero skips the five reads and reset write;
both branches still run self-test. The caller supplies `true` to `GetDdrSkipTap`.
The helper's false mode independently performs no reads or output stores and returns
zero; that is not the selected call in this parent branch.

The exact five-read order and output argument ordering are:

| Offset | Mask | Output pointer |
| --- | --- | --- |
| `0x14a0` | `0x3f` | argument 1, 32 bits |
| `0x14a4` | `0xfff` | argument 3, zero-extended to 64 bits |
| `0x1498` | `0xfff` | argument 2, zero-extended to 64 bits |
| `0x14ac` | `0xfff` | argument 4, zero-extended to 64 bits |
| `0x14b4` | `0x3ff` | argument 5, zero-extended to 64 bits |

Argument 6 receives zero. Each read status overwrites the previous one; only the last
is returned, and the parent ignores it. The parent logs argument 1. These words do not
select a branch in the recovered true-mode helper.

## Completion, clock check and fallback

`SelfTest` always attempts two reads. It reads `0x1008` into a shared, uncleared
status object, extracts bit 29 into the caller's byte, and retains that first read's
status for its own return. It then reads `0x1210` through `GetCheckAdcClk`; this second
status is ignored by `SelfTest`. The clock predicate only changes logging in this
region. It does not control the caller's retry or fallback decision.

The clock helper converts the unsigned word to binary32 and tests the strict interval
`62500f * (1f - 0.0001f) < value < 62500f * (1f + 0.0001f)`. Exact constant bits are
`0x47742400` and `0x38d1b717`. Binary32 bounds are `62493.75` and `62506.25`, so integer
words `62494..62506` pass. This is a software predicate, not a clock measurement.

The parent first calls self-test once. If its completion byte is false, it initializes
200 retries. Each retry requests `usleep(50000)`, decrements the counter, calls the
whole self-test again and logs the result. The bound is 201 self-test invocations:
201 reads at each offset, 402 mapped read attempts and 200 sleep requests. Ten seconds
is the nominal sum of requested sleeps, not an observed hardware completion time.

If the final completion byte is still false, `MemoryBram(true)` writes
`(post_last_selftest_object & 0x7fffffff) | 0x80000000` to `0x1008`. Both complete and
fallback paths then enter calibration. The software name does not prove a physical
BRAM mode. If a lower read path returns without updating the destination, the extracted
bit or fallback input may be stale. The stock mapped-load path normally writes its
loaded word and returns zero; its null-base branch can leave the destination unchanged.

## Parent continuation and explicit unknown leaves

After the DDR paths rejoin, `Drv_Init` calls calibration initialization, sets ADC data
mode 4 for selectors 0 and 1, performs one core-alignment call followed by a 1000 us sleep,
and sets AFE offset `0x8000` for channels 0 through 3. Those four offset writes target
`0x1418`, `0x141c`, `0x1420` and `0x1424` in order.

It then gets the sample-channel mask from driver setting selector 2 and calls ADC
bit-range configuration with bytes `01 01 01 01`. The downstream write to `0x1014`
is `((live_shadow | 1) & 0xff0fffff) | ((selector & 15) << 20)`; `chn2log` supplies
the runtime selector. Next are channel scale `(0,100000000)`, two Sinc calls
`(1,1,2,200,1)` and `(1,1,3,200,1)`, fan speed `(0,1.0)`, and scope startup with the
saved original initialization bool. Four AFE-enable calls follow, one per channel.

Finally, three shared-shadow writes to `0x4008` clear bit 26, clear bit 24, then set
bit 23. Every write uses the then-live shadow; sequential formula chaining assumes no
intervening mutation. None of these callee statuses controls the parent tail.

Normal `Drv_Init` return is always zero. The factory caller supplies false and also
forces its own return to zero. The low-power restoration caller supplies true and
continues without inspecting the result. Normal return alone therefore cannot serve
as an initialization-success test. Stack-canary failure is a separate terminal path.

Calibration initialization, active core alignment, channel-scale configuration, Sinc,
fan transport, scope startup and AFE-enable internals remain explicit bounded leaves.
Calibration itself includes loaders, hardware calibration and thread startup; scope
startup includes runtime/DMA initialization. Parent ordering is recovered, while their
transitive hardware and asynchronous contracts remain open. The next experiment must
stop before crossing an unrecovered leaf or first recover that leaf.

## ABI correlation and next observation boundary

The recovered pre-calibration accesses use the established SCU/SPU wrappers and
`Dev_ReadRegister`/`Dev_WriteRegister`; they introduce no new device node, ioctl, DMA
buffer or interrupt interface. They are four-byte accesses within the existing 16 MiB
mapping. The previously pinned [XDMA reference](xdma-boundary.md) explains BAR mapping
plumbing, not reset values or FPGA behavior. No new kernel mechanism is justified by
this region.

A region-scale candidate can supply distinct version/tap words, a chosen completion
sequence and a coherent clock-counter fixture, while checking stock composition,
output masks, live selectors, shadow writes and the post-self-test branch. The
calibration call is a useful terminal boundary. A ready bit would be explicitly
synthetic; it would establish only that this stock initialization region consumes that
fixture as predicted. Useful UI and credible acquisition remain separate milestones.

Reproduce the static graph with:

```sh
kotlin tools/research/RecoverInitTail.main.kts STOCK_ELF NEW_OUTPUT_DIRECTORY
kotlin tools/research/VerifyInitTail.main.kts STOCK_ELF NEW_OUTPUT_DIRECTORY/grammar.toml
```
