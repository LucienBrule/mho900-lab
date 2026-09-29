# Physical private-cache observation

One guest-validated passive observation reached the running stock Setup object
through service 38 in a 49-entry registry. Both cache windows were preserved and
independently verified. This is physical-process evidence, not a stored FRAM image.

The reader performed 122 read-only process-memory reads totaling 9,336 bytes.
It checked the registered base adjustment, backlink, three Setup vtables and RTTI
headers, CFram metadata, readable mappings and bracketed ownership metadata.
Two observations matched, as did the working and reference private windows.
The APK/native pins, process epoch and relevant mappings remained stable.

Each private stream is 204 bytes and contains record 16192 (8 bytes, saved time)
and record 2337 (148 bytes, encrypted key backup). Compared privately with the
acquired-input guest model, the encrypted-key-backup payload is byte-identical;
the saved-time payload differs. Record ordering also differs. Thus the key-backup
model has direct cache corroboration, while the complete serialized streams must
not be called identical. Unit-specific payloads remain in the private corpus.

No live MemFile list was reconstructed. The caches can lag un-serialized logical
records, and their agreement does not prove device readback, atomicity or power-loss
durability. The earlier SD acquisition still does not include physical FRAM.

## Acquisition and restoration

A fresh full Layer Two capture retained 42,989 complete frames with zero kernel
drops. The recorder exited gracefully with status 0. Its SHA-256 is
`1180ff202ebe04e4dcb0ccce80dbe09c37c966eb8ad7b1c84a364fc379afc02d`.
The recorded traffic classifier accepted every retained frame. Host-originated
local discovery permitted by the established address-assignment control remains
in the capture; there is no claim that every frame originated from the scope.

The scope-facing interface was rechecked, the default route remained elsewhere,
and forwarding/Internet Sharing/NAT were absent. The existing six-hour private
lease was sufficient; the responder was available only for that pinned client.
The temporary host address was removed, ADB disconnected, responder stopped and
host preference/network-interface plists remained byte-identical. The device's
reported enforcement state was unchanged. No new visual UI report was available
at sealing, so visual stability is not asserted as an independently observed fact.

The initial host-only audit lacked a usable shell PATH and retained command
resolution errors. A complete new audit was preserved after fixing that shell's
environment, before contact. A controller interpretation check also caught an
absent manifest field before execution. Both are preparation evidence; there was
one actual physical reader execution and no retry.

Helper staging and its evidence files are explicit writes under a unique temporary
device directory, retained as residue. The reader did not attach to Sparrow, call
its methods, write its memory, acquire its locks, use I2C, install an option, reboot
or change capabilities. Cached private bytes and all raw partial-capable read
artifacts are retained separately from the guest control.

Full acquisition seal: `78a127c2a82f1d94fd98df3ca9bf7a5a9ceabac17e9d4f5d753522e9c8e27575` (279 members).

## Decision

The working/reference cache question is closed positively. The next preservation
question is **whether two bounded reads of the actual 8192-byte device backing
this exact CFram descriptor agree, and whether its private region agrees with the
captured cache**. The ordinary installer should not be treated as having a complete
private-state backup until this remaining device-storage boundary is resolved or
its limitation is explicitly accepted.

Stock page-read semantics are already recovered: two-byte offset selection plus
read in one combined request, in 16-byte chunks. A new acquisition helper must
require exact completion of both messages, bind the existing stock descriptor to
its actual adapter/device identity, limit all offsets/counts, preserve failures and
avoid forcing a driver address or issuing any data-writing transaction. That is a
separate task and is not performed by this cache observation.
