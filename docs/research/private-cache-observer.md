# Passive private-cache observer

The reader implements the [recovered Setup ownership path](private-state-acquisition.md)
without calling into the target. It is a separate profile from the prior two-word
bandwidth observer. Stock APK and native-library hashes remain pinned.

It resolves service 38 through the stock registry, verifies the registered-base
adjustment, backlink, three vptrs and RTTI headers, and reads the two private cache
windows at offset 0x100. Registry, selected item and complete Setup metadata are
read again after each pair of windows. The two observations must match, with
working/reference divergence reported separately. The full Setup comparison is
intentionally conservative: unrelated mutable fields can cause a recorded rejection.

Active registry entries are limited to 64, capacity to 128, and each private window
to 1792 bytes. At those bounds, two observations request at most 9,696 target bytes
in 152 reads; the hard ceiling is 16 KiB. Every attempted read has a raw artifact,
including a short or failed read. Pointer ranges must be readable private anonymous
memory outside the library image; fixed structural data comes from the verified
stock mapping. Cache allocations must not overlap each other or the Setup object.

The native observer also retains PID/start-time, boot identity, backing APK hashes
and metadata, selected module mappings, and mappings covering every actual read.
It opens process memory read-only and performs no target attachment, method call,
lock acquisition, memory write or device I/O. Helper execution and evidence output
are operations of the observer, not operations inside Sparrow.

## Preparation validation

The ARM64 static reader and synthetic fixture compile with warnings treated as
errors using pinned compiler/linker binaries. Build manifests match their files;
ELF headers and controller syntax checks pass. The actual new C mapping resolver
passed one positive and nine rejection comparisons against the Python oracle,
with 16 Python controls, two ELF controls and two SHA-256 controls. The pure private
stream/observation core separately passed 24 controls and six independent boundary
checks as recorded in the acquisition report.

The synthetic fixture maps the original APK privately and supplies a fabricated
Setup registry/object and two empty, valid MemFile streams. It does not execute
stock initialization or access an instrument device. Its broken-backlink variant
is intended to prove rejection before cache payload reads. Preparation establishes
readiness for that guest control, not readiness for physical deployment.

## Interpretation limits

Even a successful guest control establishes observer plumbing against a synthetic
object graph. It cannot establish the live specimen's owner lifetime, whether
software mirrors match the physical device, or durable FRAM state. Repeated matching
observations are non-atomic. A physical application may legitimately reject this
conservative profile; preserve that result before choosing any narrower comparison
or revised bound. Physical use requires its own admitted capture and isolation run.
