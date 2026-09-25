# Calibration initialization: static contract

The preceding stock run stopped before `Drv_GetScope` at `0x2e57f8`. Static recovery
now covers the calibration dispatcher and selected environment/transport helpers.
It does not claim complete transitive recovery of every calibration algorithm.

`Drv_GetScope` returns a fixed global at library base plus `0x10bee40`.
`GetCalibration` returns that object plus `0x60d8`. `CCalibration::Init`,
`0x333afc..0x333dc4`, initializes local buffers, loads calibration data, programs
ADC parameters, invokes later calibration algorithms and starts a worker thread.
Most returned statuses are stored and overwritten without affecting dispatcher
control flow. The DDR loader is an exception: a signed result at least one invokes
DDR configuration; zero or negative skips it.

The complete dispatcher call inventory and typed graph are in the
[calibration manifests](../../experiments/calibration-static/scope.toml).
They distinguish deterministic call/loop structure, runtime inputs, hardware
feedback, asynchronous work and unresolved effects. The raw inventory resolves
direct branches and PLT relocation targets from the pinned ELF; unresolved direct
targets and indirect calls remain explicit. Byte agreement alone is not a proof
of the semantic annotations.

The first three loaders read LSB, vertical and ADC calibration records, then
`SetADCParameter(0)` applies their state. This happens before the remaining AFE,
clock, external, DDR, AFG, ADC-stray and LA loaders. The AFG loop uses selectors
one and two; the ADC-stray loop uses zero through three. Those software loop
bounds do not require runtime rediscovery.

The checked binary loader uses a 28-byte little-endian header: header CRC,
header-body length 20, opaque metadata, payload length and payload CRC. The
`.hex` suffix does not imply text. Missing/open failure returns `-1`; structural
failure returns `-2`; integrity or embedded-length failure returns `-3`. A failed
payload CRC occurs after copying into the destination. Failure therefore does
not generally mean the destination was preserved. A short payload read may also
overwrite a prefix before returning `-2`.

Two extracted defaults are available and their CRCs validate: LSB contains 192
payload bytes, and vertical contains `0x1b60c0` payload bytes. Neither the primary
nor default ADC record exists at the inspected corpus paths. This inventory is
about the extracted corpus, not the physical instrument or current guest.

The initial ADC parameter routine has a recoverable mode-zero call shape:
two reference updates, sixteen gain-fine values, sixteen core-gain helper calls,
an ADC-stray application, sixteen core-offset helper calls, delay application
and ADC synchronization. Operands depend on mutable calibration fields and live
shadows. The existing ADC transport grammar explains paired writes at `0x3000`
and a 100-microsecond delay; it does not supply those operands or prove that the
FPGA acted on the writes.

Later synchronization and alignment use hardware feedback. Their unresolved
algorithms remain named graph boundaries. Thread concurrency begins during
`std::thread` construction; detach occurs afterward. The bound virtual entry is
`CCalibration::run`, whose body is outside the recovered initialization dispatcher.
Future observation must account for that worker before admitting its effects.

The immediate modeling choice depends on file outcomes and the initial ADC
destination state. A useful next experiment should validate a complete loader
region or coherent parameter region at those ambiguity boundaries. It should
not discover the next deterministic store one instruction at a time.

Constructor inspection found no writes to the ADC record at subobject offsets
`0x8804..0x8f93`. Its first consumed references are signed halfwords at `0x8854`
and `0x8856`. The complete record resides in ELF zero-filled storage at library
base plus `0x10cd734`, with no relocations inside it. The inspected constructors
do not overwrite those initial zeros. This establishes image-initial state;
the live record can still reflect earlier writes or partial loading attempts.
Missing both files alone therefore does not establish its live contents.
Capture the resulting record before applying ADC parameters, or establish an
independently justified complete input record.
