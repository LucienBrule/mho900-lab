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
memory is requested. Two samples transfer at most 48 bytes of target memory. Their equality is a repeated
observation, not an atomic snapshot guarantee.

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
