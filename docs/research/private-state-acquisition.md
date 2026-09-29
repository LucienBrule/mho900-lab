# Private-state acquisition boundary

The next preservation step should distinguish three software representations
before claiming anything about physical FRAM: live `MemFile` records, the `CFram`
working cache, and its reference mirror. None alone is a durable device image.
This is static recovery from stock Auklet, not a new observation of the specimen.

## Provenance and recovered layout

The stock native SHA-256 is
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`.
The retained private-storage disassembly contains 5,770 unique instruction words;
all were compared against the corresponding ELF load-segment bytes by
`tools/guest/verify-private-storage-assembly.py`. Byte agreement establishes the
source of the disassembly, not independent proof of every interpretation.

| Representation | Recovered structure | Supporting virtual addresses |
| --- | --- | --- |
| Setup service | Embeds `CFram` at `this + 0x58`; constructs it with size 8192 and address 0x50 | `0x3f0c7c–0x3f0c88` |
| `CFram` header | fd at +0, device address at +4, size at +8, working pointer at +0x10, reference pointer at +0x18, mutex at +0x20 | constructor `0x3bd4b4` |
| Working cache | `getDiskBuf` returns +0x10; cache `write` changes this buffer | `0x3bd7c8`, `0x3bd8f4` |
| Reference mirror | Loaded from the device, then updated per successfully reported changed span during flush | `0x3bda08`, `0x3bddac` |
| Private serialized region | Begins at cache offset 0x100; save requires serialized length below 0x700 | `0x3f7830`, `0x3f5e28`, `0x3f5e90` |
| Live `MemFile` | Global `mPrivateData` at 0x151b3f0; modified byte at +0, list object at +8 | `0x3f1ebc`, `0x3f307c` |
| Live `SegFile` | 20-byte attribute header; payload pointer at +0x18, separate allocation | `0x3f1550`, `0x3f1b64` |

`MemFile.serialOut` iterates its list and serializes each `SegFile`. Reading bytes
at the global object address is therefore not equivalent to reading the private
stream. Invoking serialization inside the physical application would also be a
new execution intervention. A separate observer should reconstruct from bounded
reads only after pointer ownership and concurrent mutation handling are proven.

## Why cache agreement is weaker than durability

`loadCache` reads into the reference buffer and copies it to the working buffer
only after its expected count succeeds. A failed load clears the reference
buffer. `flushCache` compares the two buffers, writes changed spans and copies
successful spans into the reference buffer. A later span failure can leave a
partially updated mirror. It is not an immutable boot image or a transactionally
committed device snapshot.

`saveSession` clears the private modified flag at `0x3f5f00`, before calling
`flushCache` at `0x3f5f14`. Thus an unmodified flag cannot establish a successful
flush. Even two equal cache observations establish only sampled software
agreement, not atomicity, absence of intervening changes, independent device
readback or power-loss durability.

## Alternatives and selected next boundary

1. **Paired cache observation:** bounded reads of the stock working/reference
   cache, with object metadata and readable-range checks, repeated observations,
   raw preservation and independent stream validation. This is the smallest next
   observation that can reveal pending differences without executing stock save
   code or touching the I2C adapter.
2. **Live MemFile traversal:** useful to distinguish records not yet serialized
   into the working cache, but requires linked-list and payload lifetime controls.
   Defer until paired-cache evidence shows that extra representation is needed.
3. **Direct stored-image read:** required for an actual FRAM acquisition. Stock
   `page_read` builds an ioctl 0x707 request with two messages: a two-byte
   big-endian offset selector (flags 0), followed by a read (flags 1). This is a
   bus transaction with an address-selection write, not a passive memory read.
   The stock wrapper checks only a negative ioctl return, not an exact two-message
   completion. Its returned byte count is consequently insufficient independent
   proof that every requested message completed.
4. **Calling stock getters/load/save:** rejected for the first observation because
   it would add application execution and potentially change cache/device state.

A future direct reader would need to require exact transaction completion, pin
adapter/device identity, bound every offset and length, preserve independent reads,
account for concurrency and stop on disagreement. No I2C operation is performed or
admitted by this analysis.

## Remaining gates

The embedded-object offset is established, but physical discovery of the owning
setup-service instance and proof of its lifetime are not yet established here.
A guessed heap address or a broad process dump is not an acceptable substitute.
The next reader must retain process identity, exact native mapping ancestry and
object metadata around every bounded sample. Repeated matching samples remain
non-atomic observations.

The bench question is: **do the running stock application's working and reference
private regions agree, and can both be preserved with a bounded read-only
observer?** After that, a separately justified device read can ask whether stored
FRAM agrees. Until then, the acquisition corpus still lacks a physical FRAM backup.
