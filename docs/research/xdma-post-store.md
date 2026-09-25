# Stock two-word state after the global store

The first run stopped at its private-controls gate because thread enumeration failed. The private paired-read
control did reach its hardware breakpoint with the expected composed value, and the unexpected-access control
stopped after one response. Stock observation did not start; Sparrow received no synthetic device responses.

This batch asks whether the existing two synthetic mapped reads reach the stock global object when observation
allows synchronization-sensitive code to execute continuously. The breakpoint is at ELF PC `0x42a8f0`, immediately
after `str x8, [x9]` at `0x42a8ec`. It stops before the following branch, function return and later converter.

The [private breakpoint controls](guest-execution-profile.md) established post-atomic delivery in this pinned guest.
The stock read offsets, instructions and dataflow remain those in the [identity-flow analysis](xdma-identity-flow.md).
The fixture supplies high word `0xe1234567` at offset `0x4048` and low word `0x89abcdef` at offset `0x4044`.
The expected masked composition is `0x0123456789abcdef`. These are deliberately synthetic values, with no claim
about physical identity or instrument register contents.

## Method and evidence boundary

The native supervisor retains the existing guarded open/mmap observation and inaccessible 16 MiB mapping. It
completes only the two witnessed 32-bit load instructions, preserving the existing PC/opcode/address/register
checks. It then installs one hardware execution breakpoint using the explicitly tested cached-enable profile and
resumes with `PTRACE_CONT`. No instruction stepping, instruction replacement or forced mutex result is used.

Before stock observation, four private width/direction controls run, followed by a positive paired-read composition
control and an unexpected second-access control. The latter must stop after one response at offset `0x4040`.
The independent controls verifier must pass before the supervisor attaches to Sparrow.

At the stock terminal stop, capture signal metadata, all general registers, stock instruction bytes, the relocated
`m_DNA` pointer, `x8`, `x9` and the eight-byte object value. Agreement among the known synthetic inputs, decoded
composition, post-store register state and memory is the intended witness. The supervisor terminates/reaps the
application after capture. An unexpected signal or device access is recorded and terminates this question without
supplying another response.

Thread inventories are captured before the modeled reads and at the terminal stop. Each records TID, thread group,
tracer identity and state, with bounded enumeration and explicit errors or overflow. These are non-atomic snapshots:
sibling threads remain runnable, can appear or exit during enumeration, and are not traced by this observer.
The stopped main thread establishes no process-wide event order or proof that siblings never accessed the mapping.
A separate thread-coverage decision is required before extending modeled device behavior.

The existing exact-stock guest admission and labeling fixture is reused; its rejection controls and restoration
checks remain required. Guest enforcement remains enabled. The stock APK and native library are preserved, and
no physical instrument or host policy change is part of the experiment.

## Run result and diagnosis

Run `post-store-01` completed on 2026-09-25 UTC. The four width/direction controls completed. The private positive
control consumed both selected words, reached PC `0x214608` with signal 5/code 4 and matching signal address,
and held `0x0123456789abcdef` in its output object and `x9`. The negative control reached offset `0x4040`, received
no second response and exited 78. Both private children were terminated/reaped with status 9.

All four private thread inventories reported `observed_count = 0`, `error = 1` and no overflow. The controls
verifier rejected that evidence, and the helper exited 3 before collecting the stock PID or attaching the stock
supervisor. The outer run's `inspection = completed` means orchestration completed; it does not override this
failed control gate. A post-run verification mode checks the exact partial outcome without treating it as success.

The source requests directory opens with flag `0x10000`. The ARM64
[reference header](https://raw.githubusercontent.com/torvalds/linux/v3.18/arch/arm64/include/uapi/asm/fcntl.h)
defines `O_DIRECTORY` as octal `040000` (`0x4000`) and `O_DIRECT` as octal `0200000` (`0x10000`). Thus the fixture
used the wrong architecture-specific flag. The capture recorded only a general inventory error, so it cannot
independently distinguish failure at open, directory reading or record parsing. Direct source-download attempts
returned HTTP 429; the reference text was inspected through the web tool, and its constants and access limitation
are recorded separately. The reference is not claimed to be the exact guest kernel source.

`system_server` retained PID 1044 across admission and observation. The installed stock APK and embedded library
hashes match the original pins; admission controls and normal instrumentation detachment completed. The guest was
shut down, with cleanup acknowledgement and free experiment ports. Sparrow remained launched during the private
controls but never received a modeled mapping or synthetic response. No stock global-store conclusion follows.
Enforcement was sampled as `Enforcing` during preflight; the helper's final enforcement sample was not reached.
The recorded source performs no enforcement change. A successor should capture final enforcement even on early exit.

## Decision

Preserve this run and admit a successor that tests both directory-open flags and records the precise failing
operation and return code, then requires valid private thread inventories before attempting the same bounded stock
post-store observation. The paired-read and hardware-stop mechanics need no behavioral expansion. Keep the two
synthetic words, terminal PC and stop conditions unchanged; this corrects an observer ABI error and makes failures
diagnosable. Thread coverage remains unresolved until inventories actually succeed.

## Reproduction

Configure `NATIVE_CC`, `NATIVE_LD` and `ANDROID_SDK_ROOT`, then use a fresh ID:

```sh
tools/guest/build-native-probe.sh
NATIVE_POST_STORE=1 tools/guest/run-admission.sh fresh-run-id native
kotlin tools/guest/VerifyPostStore.main.kts out/guest-admission/fresh-run-id
```
