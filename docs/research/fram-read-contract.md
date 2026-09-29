# Bounded stored-FRAM read contract

The offline transaction core in `tools/guest/fram-contract/fram-read.h` is a
preparation for acquisition, not a device reader. It has no open, ioctl, process
attachment or networking implementation. No physical FRAM transaction was performed
in this batch. The preceding [paired-cache observation](physical-private-cache.md)
remains software-cache evidence, not a stored-device backup.

## Stock consumer and reference boundary

The pinned stock Auklet described in [private-state acquisition](private-state-acquisition.md)
constructs an 8192-byte CFram at address 0x50. Its `fram_read` uses 16-byte chunks;
`page_read` sends a two-byte big-endian offset selector followed by a read through
ioctl 0x707. The stock wrapper rejects negative return values but does not require
exactly two completed messages. The acquisition contract deliberately adds that
completion check rather than treating the stock byte-count return as proof.

The public reverse-engineered kernel reference is a separate source of Linux ABI
semantics, not evidence of the physical instrument's exact kernel. Its recorded
revision is `d23adbd11626f12abaf4bc742e250204fe2b9f8a`. The original local extract
contains only 16 XDMA/libxdma files, not I2C sources. During this review 15 matched
the recorded pins; `drivers/rigol/libxdma/libxdma.c` did not. Its expected SHA-256
is `ae2ccf14fed3d30740263a3f7dc79f0705b67ddddfc5d5ada26bd35688965ae8`, and its
observed SHA-256 is `898cca08084ffa843a60e6aba025def4c871fc59115299565e838f2f4aad168a`.
The differing file was preserved and excluded from this contract's evidence.
The cause and any implications for earlier uses require separate reconciliation;
no conclusion here depends on that file.

The four I2C files were acquired separately at that exact revision, with SHA-256
and Git-blob identities recorded in `experiments/fram-contract/reference.toml`.
The reference `include/uapi/linux/i2c.h:68–81` defines the message layout;
`include/uapi/linux/i2c-dev.h:49,64–67` defines ioctl 0x707 and its request.
`drivers/i2c/i2c-dev.c:314–325` forwards the transfer result, subject to copy-out
failure; `drivers/i2c/i2c-core.c:2305` defines it as the completed-message count.
The wrapper copies read buffers for any nonnegative result, so populated bytes
cannot replace the exact-completion check. Extracted reference declarations also
passed an independent ARM64 layout compilation. These are reference-code facts,
not identification of the specimen kernel.

## Core guarantees and controls

The injected transaction callback receives exactly two messages at address 0x50:
flags 0 / length 2 for offset selection, then flags 1 / length 16 for data.
Only aligned offsets 0 through 8176 are accepted. A full image is 512 transactions
and 8192 bytes. A callback result other than 2 stops immediately without retries;
the failed page is not copied into the accepted output. On failure the completed
prefix length is explicit. A future syscall wrapper must preserve attempted
messages, return value, errno and partial raw buffers separately before returning
control; this core does not retain failed scratch buffers itself.

Host controls cover a complete patterned image, all offset bytes, negative/zero/
one-message/impossible-three-message returns, an accepted prefix followed by
failure, invalid offsets, null arguments, matching repeated reads and differing
repeated reads. AddressSanitizer and UndefinedBehaviorSanitizer pass. Cross-compiling
the assertions for ARM64 Android API 25 verifies a 16-byte message with buffer
pointer at +8 and a 16-byte request with message count at +8. This proves the
chosen C layout; reference UAPI comparison supplies the distinct ABI evidence.

Run the reproducible controls with configurable compilers:

```sh
python3 tools/guest/fram-contract/verify.py \
  --output out/fram-contract-control \
  --host-cc clang --cross-cc "$ARM64_CLANG"
```

The runner requires a new output directory, retains compiler/test output, hashes
source files and seals the resulting artifacts. It does not use an Android guest
or contact any device.

## Decision and remaining acquisition gates

The exact-completion core is ready for a narrowly scoped wrapper, not physical
execution. The next batch should first bind the live CFram descriptor to the
actual adapter node, character-device identity and kernel metadata. Do not infer
the adapter from a historical path or enumeration number. Pin process/boot/module
identity and confirm the observed CFram capacity and address again.

A wrapper must use only the combined selector/read operation, with no forced
slave selection, stored-data write, adapter scan, application callback or retry.
Prove its syscall construction and failure-artifact preservation using a disposable
control before considering physical use. A physical plan needs fresh packet
capture, verified host isolation, exact command and artifact bounds, two separately
preserved 8192-byte reads and a comparison against the captured caches. Matching
reads remain non-atomic observations: concurrent stock saves and the adapter's
behavior must be recorded, not assumed away. Any transfer failure or disagreement
is a stop condition.

The exact bench question is: **does an identity-bound, fully completed direct
FRAM read contain the same private record 2337 payload as the independently
captured working/reference caches, and do two complete reads agree?** This session
stops at the offline contract checkpoint. It does not install physical options,
change capabilities, reboot the instrument or claim a durable FRAM backup.
