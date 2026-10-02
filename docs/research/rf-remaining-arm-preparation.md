# Remaining RF arm preparation

The preparation gate is complete for the remaining derived and final-stock
transitions and the three matched capture arms. This is an offline conclusion.
Actual process, visible UI, lease, warmup, preservation and capture evidence must
still pass before an arm can be accepted.

Each transition retains the previously reviewed native selection, single reboot,
no-retry behavior, serviced warmup exceeding 1,800 seconds, bounded process
observation and graceful capture termination. The only calibration comparator
change is the [confirmed eight-byte timestamp](rf-stock-timestamp-check.md).
Fixed metadata, both CRCs and all coefficients remain protected.

Historical introduced-file provenance and current process acceptance are
separate inputs. The derived transition retains the original deployment lineage
while binding the accepted current stock process and its logical corpus. The
final-stock transition must bind the actual derived deployment and its new
postboot DHCP ACK. The earlier partial transition remains partial evidence; its
captured ACK can supply lease authority through a narrowly checked adapter,
but it cannot establish an accepted RF arm.

The first stock boot visibly restored ordinary settings to 50 mV/div and
2 microseconds/div. A captured normalization now saves the full actual query
snapshot, checks the existing electrical prerequisites, and sets only ordinary
scale, timebase and memory depth as needed. It then verifies the original
500 mV/div, 10 ns/div, 10,000-point, 4 GSa/s preconditions. A stopped acquisition
or changed electrical path rejects before normalization writes.

Actual collection remains 50 mV/div, 1 microsecond/div, 100,000 RAW points at
4 GSa/s. Each arm visits 100, 800, 975, 1,000 and 100 MHz, collecting five records
at each visit. The source command, RAW eligibility and numerical sections are
unchanged. Restoration deliberately uses the saved pre-normalization snapshot;
this reversible extension is separately identified in the generated diff.

The typed arm projection requires the actual candidate, full mapping rows,
installed APK, epoch-bound visible-UI receipt, explicit independent decision,
and hashes of the raw-run and independent-review manifests. It checks stock
17/17 versus derived 18/18 and carries every evidence binding forward. Synthetic
fixtures test these checks without asserting a physical arm.

Eight preparation-owner controls, 35 independent binding/configuration controls
and 15 separate source/body controls passed. Newly authored modules and tests
passed strict type checking, lint and formatting. Retained legacy executors are
not claimed to be newly typed code. Both transition bodies preserve 23 callback
ASTs; all three capture arms preserve the numerical and source sections.

Preparation is preserved in
`out/rf/remaining-transition-preparation-20261002T025700Z.toml`, SHA-256
`2e3b773b7675f0cac590a9340352c6b9eb6a6599a1dc39ef9e8d7f79f873c2cf`.
Its 129 artifacts total 25,956,336 bytes and include source, generated fixtures,
exact diffs, verification logs and the local invocation guide.

The independent 35-control review is preserved in
`out/rf/remaining-transition-independent-20261002T025600Z.toml`, SHA-256
`19c4eedf0640077cb637196bbe53c8745c2e8d4019dba1680b78fcefb44e0d82`.
This is a custom regular-file inventory, not a native evidence manifest.
The separate 15-control review is native-sealed at
`out/rf/remaining-transition-independent-review-20261002T030200Z.toml`, SHA-256
`3dd42eed48d7e10117fe069d6c974df5e26361c69c3a7064e241e42b0543c18d`.
All three inventories were independently rehashed before task closure.

The preparation conclusion permits concrete binding of future runs. It does not
release RF collection before the stock continuation and execution decisions,
and it does not establish analog bandwidth or a result of the comparison.
