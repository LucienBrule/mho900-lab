# Calibration contract review

The review checks the recovered calibration dispatcher against the pinned stock
library. It keeps the original recovery bundle intact and records corrections
and qualifications in [review-refinements.toml](../../experiments/calibration-static/review-refinements.toml).
Future consumers must apply those refinements alongside the original manifests.

The dispatcher orders LSB, vertical and ADC loaders before `SetADCParameter(0)`.
The AFG selectors are one and two; ADC stray selectors are zero through three.
The initial direct reference operands are signed halfwords, but they are only
the first mutable inputs. Mode zero also consumes core gains, sixteen SPU gain
words, offsets and delays. The recovered ten-entry software index table selects
a contiguous sixteen-word span for mode zero. It supplies indices, not measured
calibration values or FPGA behavior.

The operation previously named `adc_state_load_loop` is the ADC stray loader.
Its direct callee is known. The original cross-reference suffix `adc-stray`
refers to loader ID `adc_stray`. These naming corrections do not alter dispatch.

Thread construction precedes the active-flag store and detach. Worker entry can
therefore precede the flag write; the flag cannot establish that entry has not
occurred. The worker body remains outside the recovered dispatcher. Similarly,
zero indirect calls in the selected twenty-two ranges does not imply zero
transitive virtual calls. The raw inventory contains thirty-seven unresolved
call sites across twelve distinct direct targets.

The next externally supplied inputs are calibration files. Two stock defaults
are available and independently match their header and payload CRCs. A bounded
filesystem fixture can provide those exact files and keep all three primary
paths and both ADC paths absent. Expected final loader statuses are 192,
`0x1b60c0` and -1 if the files are accessible. A different result is evidence
about the guest environment, not permission to synthesize success.

A coherent observation region spans all three loaders. Capture signed `w0`
immediately after each call at `0x333b78`, `0x333b84` and `0x333b9c`; stop before
ADC programming at `0x333ba8`. At that final stop, the ADC status resides at
`sp+0x74` and `x0` already contains the ADC object pointer. Validate complete
LSB and vertical destination payloads against their files, and compare the
complete ADC record before and after loading. A negative return does not imply
an unchanged destination.

Those checkpoints need no new mapped-register responses. Existing threads still
require coverage, and final full-buffer capture requires a converged group stop
before making a simultaneous-state claim. The calibration worker is created
later in the dispatcher. An unexpected clone, mapped access, wrong checkpoint,
short capture or changed binding must end the bounded observation.

The [stock kernel ABI contract](kernel-abi-contract.md) remains the plumbing
reference. This loader region requires no extension to its mmap, ioctl or DMA
model. The pinned public kernel comparison remains separate from stock-binary
evidence and from any modeled FPGA behavior.

The recovered parameter sequence remains symbolic beyond this boundary. Actual
FPGA reset state, read side effects, completion timing and DMA behavior remain
unestablished. The review does not turn the kernel reference or software call
ordering into physical-instrument evidence.

The verifier reads ELF program headers, symbols, relocations and instruction
words independently of the recovery tool. It checks the full selected call-site
set, PLT bindings, dispatcher edges, loop witnesses, loader records, initial
storage placement and the candidate checkpoints. Manual disassembly review
supplies the higher-level interpretation. Isolated altered manifests receive
updated artifact hashes before verification, so rejection exercises structural
or byte-level checks rather than merely stale hashes. This is bounded evidence,
not a general proof of every semantic annotation or deeper callee.

Reproduce the verifier controls using `kotlinc -script` (the driver itself
launches Kotlin compiler processes):

```sh
kotlinc -script tools/research/CheckCalibrationContract.main.kts -- \
  local/reversing/firmware-extracted/stock-0.26/sparrow/base/lib/arm64-v8a/libscope-auklet.so \
  experiments/calibration-static tools/research/VerifyCalibrationContract.main.kts \
  out/calibration-static/review-repeat
```

Use a fresh output directory; the driver rejects an existing one. The corpus
must already be present locally. The source repository does not contain it.
