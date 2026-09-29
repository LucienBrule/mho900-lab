# Stock specimen entitlement boundary

Current status: [overnight entitlement handoff](overnight-entitlement-handoff.md). This report preserves its
original experiment history; later acceptance and persistence results are linked from the handoff.

The ordinary installer is recoverable without tracing ADC initialization again. Its success cannot be judged
from the outer return value, and the acquired SD image does not contain all of its persistent inputs.
These are static implementation findings, not a physical option-state query or a completed guest installation.

The active specimen Auklet and official `.26` were freshly hashed and both equal
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`.
Addresses below are ELF virtual addresses for that exact library. Disassembly and private archive inventories
remain under `out/overnight/`; the public manifest pins the relevant disassemblies.

## Ordinary interface

| Operation | Native entry | ELF address |
| --- | --- | --- |
| Install an ordinary option | `CApiLicense::ApiLicense_SetLicenseInstall(RString)` | `0x4332fc` |
| Query validity | `CApiLicense::ApiLicense_GetLicenseValid(OptType,bool&)` | `0x43254c` |
| Query option list | `CApiLicense::ApiLicense_GetLicenseList(RString&)` | `0x432738` |
| Initialize the license service | `CApiLicense::init()` | `0x434de4` |
| Write an accepted token | `CApiLicense::writeLicense(OptType,RString&)` | `0x438e70` |

License service ID is 36. Its install, validity, list and changed messages are respectively 11009, 11008,
11010 and 11017. `ApiLicense_SetLicenseKey` is a separate key-material replacement operation; it is not the
ordinary installer. The native parser contains SCPI option-install and query registrations. This is
implementation-derived evidence, not a claim that every spelling is documented by the vendor.

The installer splits `<family>-<option-name>@<token>`, checks the model-family prefix, trims the option and token,
and calls `activeOpt`. Malformed splits or family rejection return -6. Once it reaches option processing,
the outer installer can return zero even when the option is rejected. Only the internal success result 24531
schedules the changed notification. Errors also travel through `syncError`.

An installation witness therefore needs error events, actual option queries, file and private-store deltas,
and reload/reboot queries. A zero return or a newly created file alone is insufficient. The installer saves
current time before its syntax checks, so even a malformed request is not necessarily a read-only operation.

## Active MHO900 catalog

For product series 900, license initialization constructs 14 records from the table at `0x151c708`, stride 40.
Initializer `0x2240c4` establishes the following names and types:

| Type | Name | Type | Name |
| ---: | --- | ---: | --- |
| 0 | BND | 1 | EMBD |
| 2 | COMP | 3 | AUTO |
| 4 | AUTOA | 5 | FlexA |
| 6 | AUDIOA | 7 | AEROA |
| 19 | RLU05 | 30 | AFG50 |
| 29 | AFG100 | 22 | BWU03T05 |
| 23 | BWU03T08 | 24 | BWU05T08 |

The Java enum is larger than this active native table. Types 1, 2 and 3 have a validity-query special case
after map membership. Their query results must not be mistaken for newly installed file-backed options.
BND can remove individual option files; a single non-bundle option is the smallest useful first trial.

## Construction and dependencies

`CApiFactory::Api_Create()` at `0x23624c` constructs real service objects, including Utility 11 and License 36.
The factory allocates 432 bytes for License. Its registry holds the `CApiBase` subobject at complete-object+8;
direct License methods require the complete-object pointer. Guessed zero-filled objects are not a valid baseline.

`Api_Init()` at `0x2390cc` immediately enters `Dev_PCIeInit`, then performs vendor and all-service initialization.
It is too broad for the first isolated license experiment. The candidate boundary is actual Android ELF loading,
stock factory construction and only the required stock initialization methods. Ordinary `dlopen` does not call
`JNI_OnLoad`; a native component harness can avoid Java startup unless the executed path proves it necessary.
This remains a hypothesis until runtime validates it.

License initialization reads exported key material, calculates private service record IDs, constructs the option
records, reads saved option files, copies cached Utility model/serial and verifies tokens. Cached identity getters
are not hardware reads themselves, but their initialization must be established. Missing services or identity
must not be replaced with invented success. License `start()` additionally manages trial time and timers;
component tests must state whether that lifecycle has executed.

The key material is runtime-derived. `ApiUtility_InitVendor` calls `ApiUtility_GetDNA` and then
`ConvertDNA2Key(fileKeys)` before its first-run check. Calling License initialization with the library's initial
data values does not reproduce specimen key initialization. Direct stock model and serial setters exist, but
they do not supply the missing DNA provenance. Copied `Key.data` alone is insufficient to establish a coherent
specimen verification baseline. A future bench question is the exact stock-composed DNA value and its associated
key derivation; do not infer that value from the model or serial string.

## Two persistence domains

Stock files live under `/rigol/data/`. The initializer reads `<option-name>.lic`; `writeLicense` writes the
name/token record, closes the stream, and uses an RFile handle for fsync/close. `Key.data` supplies verification
material. All five acquired logical archives contain zero `.lic` members. This does not establish the specimen's
queried option states, trial state or defaults. Captured key and vendor files remain private.

There is also external private storage. `CApiSetup::loadPrivacy()` at `0x3f75d0` opens `/dev/i2c-4` through CFram.
The stock setup constructor configures 8192 bytes and device address `0x50`. It loads a cache and deserializes a
MemFile from physical offset `0x100`. `getPrivateBase(service)` returns `service * 64` as a logical record-ID
base, not a byte offset into FRAM; global `mPrivateData` is at `0x151b3f0`.
Trial counters, time and a decoded key backup use this store. `getLicenseKey` can synchronize its decoded file
into the private store and request `API_Save2Fram`, so initialization itself can request persistence.

The SD reads and logical archives do not establish the contents of that I2C-backed store. An empty, file-backed
guest model can support explicitly synthetic experiments; it cannot be called a complete specimen baseline.

**Bench question:** What 8192-byte image does stock CFram read at bus 4/address `0x50`, and does its private
payload at offset `0x100` agree with the stock in-memory serialization? A later procedure must first establish
safe read semantics. No physical access is part of this investigation.

## Bounded next experiment

Load unchanged specimen-derived Auklet in an isolated API-25 native process, construct real factory services,
and inspect the identity and initialization dependencies before ordinary option queries. Use copied unit files
on disposable persistent guest storage. Stop at the first stock error or externally unsatisfied dependency.
Do not install an option or redirect a capability during this baseline.

If private-store state blocks the baseline, close that question and admit an explicit synthetic-store experiment.
An eventual installation trial must retain before, after, process-restart and guest-reboot states. Native component
success remains distinct from full Sparrow startup and from physical instrument behavior. The D-capability
experiment remains separate from ordinary option installation.
