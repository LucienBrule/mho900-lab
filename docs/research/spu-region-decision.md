# Decision: recover the remaining initialization grammar

The [stock SPU result](stock-spu-region.md) confirms 460 predicted stores: all 452 ADC
stores and all eight SPU stores. Captured writable records selected gain mode 1 and
range mode 4 independently. The next uncompleted store is `W32(0x4004,0x80000000)`.
These results support whole-region prediction; they establish neither FPGA effects
nor physical acceptance of the synthetic identity.

Static recovery predicts two SCU stores, board-power UART notification, a GD32 reset
on the false initialization branch, and two LA reset stores. The mapped operands are
conditional on separate writable SCU and LA shadows. The intervening transport is a
material ambiguity: `/dev/ttyS0` open failure is ignored, but a nonpositive board-power
write terminates the process. GD32 may reopen a cached descriptor after obtaining a
one-byte value from `/dev/hdcode_gpio` into a four-byte integer. That read precedes the mapped
version reads. A mapped-only transcript would omit an important hardware-returned input.

Recover this entire region, including delegated UART setup and version consumers,
before extending the observer. Produce a typed graph with explicit branch and data
conditions, static candidate writes, pinned bytes, and distinct hardware-returned and
runtime-selected nodes. The source evidence is the unchanged stock library; public
XDMA code cannot supply the UART or FPGA side of these contracts.

The next batch contains static recovery and an architecture decision. It admits no
guest execution or new synthetic response. Its decision will select syscall observation,
native checkpoints, or a justified combination after considering synchronization and
thread coverage. A useful runtime experiment should validate the region and stop at a
real response ambiguity, unexpected transport outcome, or disagreement with prediction.
It should not rediscover each deterministic store separately.

The initial static review is retained at
`out/spu-transcript/remaining-init-decision-review.md`, SHA-256
`ebceaa18bb807605c601e0a12d4b0df12990065c304cc88cb17a5e13d1d33d9b`.
Its transitive setup paths remain inputs to recovery, not completed evidence. Commit
and push this decision and admitted tasking before execution; commit and push each
subsequent conclusion before dependent work.

The original review confused requested count with buffer capacity; the
[completed static recovery](remaining-initialization-grammar.md) records the correction.
