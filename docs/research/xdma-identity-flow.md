# Stock two-word identity dataflow

The stock consumer combines the words at mapped offsets `0x4048` and `0x4044`, masks the result to 57 bits,
stores it in `CApiUtility::m_DNA`, and passes it into a four-word transformation. The intervening driver wrapper
returns zero without propagating the lower routine's status. These are static findings about the stock program.
No new guest run or synthetic response was performed in this batch.

## Evidence and scope

The input is the unchanged stock `.26` ARM64 `libscope-auklet.so`, SHA-256
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`.
Addresses below are ELF virtual addresses, before the runtime load bias. The capture script checks this hash
before and after inspection and records LLVM version, tool hashes, dynamic symbols, relocations and disassembly.
The [results manifest](../../experiments/xdma-identity-flow/results.toml) pins the local evidence.

The [previous paired experiment](xdma-single-read.md) directly observed each selected synthetic first word
being stored by stock code before stopping at the next read, offset `0x4044`. Neither run completed that second
read. The caller chain was also present in the earlier [native capture](xdma-native.md).
Assembly, return, global storage and conversion after the second read remain statically decoded behavior;
this batch supplies no dynamic witness for them.

The names `GetFPGADNA`, `m_DNA` and `fileKeys` come from stock symbols. They do not independently establish
physical register semantics, a physical instrument identity, or the meaning of later vendor-data processing.

## Composition and status

`DevSystemSCU_GetFPGADNA` occupies `0x2853ac` through `0x28546b`.

| Operation | Instruction evidence |
| --- | --- |
| Initialize both word outputs to zero | `0x2853cc`, `0x2853d0` |
| Read high word H from offset `0x4048` | Call at `0x2853e0` |
| Read low word L from offset `0x4044` | Call at `0x2853f0` |
| Add the two returned statuses modulo 32 bits | `0x2853f8` |
| Insert H into bits 32–63 of L | `bfi` at `0x285420`, store at `0x285424` |
| Keep the low 57 bits | AND at `0x285430`, store at `0x285434` |
| Return the summed status | `0x285458` through `0x285464` |

The resulting value is:

```text
D = ((uint64_t(H) << 32) | L) & 0x01ffffffffffffff
  = (uint64_t(H & 0x01ffffff) << 32) | L
```

Both reads are attempted on the normal path; neither returned status causes an early branch in this routine.
The final exceptional branch checks the stack canary, not the assembled value.

`Drv_System_GetFPGADNA(unsigned long long&)`, at `0x2f18f8`, zeroes the caller output at `0x2f1910` and calls
the lower routine at `0x2f191c`. It then reloads its own zero-initialized local status at `0x2f1920` and returns
that value. It does not propagate the lower routine's return value. This conclusion concerns normal return
through the inspected stock definitions; it is not a claim about exceptional termination or every linkage scenario.

## First downstream storage and comparison

`CApiUtility::ApiUtility_GetDNA`, at `0x42a7dc`, calls the wrapper at `0x42a800` and checks its status with
`cbz w0` at `0x42a804`. The success path stores the assembled output at `0x42a8ec`; the failure path stores
`UINT64_MAX` at `0x42a818`. Relocation slot `0xb8d758` identifies the destination as `CApiUtility::m_DNA`,
an eight-byte object at `0xbbccf0`. Under the wrapper's decoded normal-return behavior, the success path is taken.

`ApiUtility_InitVendor` calls the getter at `0x42a2a8`, then calls `ApiUtility_ConvertDNA2Key` at `0x42a2b4`.
Its output argument comes from relocation slot `0xb8cff0`, which identifies `fileKeys`, a 16-byte object at
`0xbbcd1c`.

The first direct comparison of D in this inspected caller chain is `D == UINT64_MAX` at `0x42a93c`, with the
derived branch at `0x42a948`. The getter's earlier branch tests status. A normally assembled 57-bit result
cannot equal this all-ones sentinel. The sentinel path fills all four output words with `0xffffffff`.

On the nonsentinel path, the converter performs these operations:

| Output | Decoded operation | Store |
| --- | --- | --- |
| `fileKeys[0]` | `F(D)` | `0x42a984` |
| `fileKeys[1]` | `F(D ^ (D >> 1))` | `0x42a9a4` |
| `fileKeys[2]` | `low32(D)` | `0x42a9bc` |
| `fileKeys[3]` | `high32(D)` | `0x42a9d0` |

F denotes the unresolved helper at `0x42f254`, called at `0x42a97c` and `0x42a99c`. Its return is stored as
32 bits. D denotes the global value at the relevant loads: the converter reloads it between helper calls.
The expressions do not establish an immutable snapshot across calls; helper side effects and concurrent writes
have not been ruled out. The disassembler's nearest-symbol label does not establish the helper's identity or purpose.
This batch does not inspect its implementation, later uses of `fileKeys`, or vendor-data processing.

## Reproduction and review

Set `LLVM_BIN` to a local LLVM tool directory, then run:

```sh
tools/guest/inspect-identity-flow.sh fresh-run-id
shasum -a 256 -c out/xdma-identity-flow/fresh-run-id/evidence-sha256.txt
```

This reads the stock ELF through the ignored `local/reversing/` reference corpus and writes ignored evidence
under `out/`. It does not start a guest. The accepted capture is `static-02`. The preliminary `static-01`
index accidentally included itself; it remains preserved. The index correction excludes itself, and all
substantive disassembly, symbol and relocation captures compare byte-identically between the two captures.

An independent read-only review reran the prior paired-run verifier and checked the composition, status handling,
global relocations and converter operations. It agreed with these findings. The review specifically retained
the limits on physical semantics, the two selected prior synthetic values, and the prior guest admission-policy
fixture. Its assertions are recorded separately in the results manifest; review is not a new runtime witness.

## Decision

The observed register pair supplies structured input that survives into global state and a downstream transform.
The next bounded question should validate the decoded composition and global store with two distinct synthetic
words, including set bits above H's retained 25 bits, and stop before entering the converter. That would test
word order, masking and storage without selecting a physical identity or depending on the unresolved helper.

Any such guest experiment needs its own admitted task batch, explicit stop condition and deterministic controls.
It is proposed here and has not been admitted or run. Physical identity values, helper semantics, later consumers,
DMA, interrupts, ordering and instrument behavior remain unresolved. This read-only batch closes at this finding.
