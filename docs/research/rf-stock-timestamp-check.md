# Stock transition and checked-record timestamp

The initial-stock experiment on 2026-10-02 reached a new boot with the original
APK-backed native library. It then stopped at a protected-record comparison.
This is a partial stock transition: it does not establish a warm stock policy
witness or authorize RF acquisition by itself.

Before the transition, four fixed process reads returned repeated derived policy
values 18/18, using 16 bytes in total. The normal UI was accepted against the
same process epoch. The controller removed the verified introduced native file
and issued one reboot request. Its client timed out; the request was not resent.
A new boot and original APK-backed executable mappings were subsequently
observed, and the postboot option statuses matched the baseline. The preservation
stop occurred before the postboot UI, warmup and stock policy observation.

The affected bandwidth record is 348 bytes, including a 320-byte coefficient
payload. Both CRC checks validate, and the entire payload is byte-identical.
Only offsets 0–3 and 12–16 changed. The existing recovered checked-stream
specification and record inspector identify bytes `[12,20)` as an eight-byte
timestamp. The controller compared `[16,28)` as fixed metadata, inadvertently
freezing the timestamp's month and year bytes.

Direct inspection of the pinned stock writer and reader confirms the eight-byte
extent. `CCheckedStream::save` receives a 64-bit time value at `0x3dcc74`, stores
it with `STR x0` at `0x3dcc7c`, and serializes eight bytes at `0x3dccd0` and
`0x3dccd4`. The two envelope words and four-byte version place that value at
file bytes `[12,20)`. The reader independently copies eight bytes. The month
is shifted by 32 bits at `0x3dcae0`, placing it at file byte 16. The helper
named `toBCD` is a no-op; its name does not establish a BCD encoding.

The actual time values decode as 2026-09-30 02:15:58 and 2026-10-02 10:24:01.
These are specimen-local metadata, not evidence of clock agreement with the
workstation. Fixed metadata at `[4,12)` and `[20,28)`, valid CRCs, exact record
lengths and all payload bytes remain required. Correcting this comparator
implements the existing timestamp allowance; it introduces no calibration
exception or calibration action.

The experiment is preserved at
`out/rf/policy-initial-stock-layout-20261002T021700Z.toml`, SHA-256
`20f64caba97213c1e830b4ac9420c09f1b149fec08190f5d6b44c11bb7034769`.
Independent review is sealed at
`out/rf/partial-transition-independent-20261002T022600Z.toml`, SHA-256
`0b726daa3cd1e0e6d52dd8ab66dc3cd265f5a00c0e2e11cc73b32bfd495d5bc7`.
The writer/reader assessment is sealed at
`out/rf/timestamp-static-assessment-20261002T023300Z.toml`, SHA-256
`4a2ca12d9aac9ce60f01bd86ddf880540ba9a8b8b83e74a241e0f2f205476acc`.
The original failed controller and captures remain immutable.

The next admitted experiment is a distinct read-only continuation. It must bind
the already observed stock process and boot, the captured 24-hour lease, fresh
protected-content and visible-UI evidence, a serviced warmup exceeding 1,800
seconds, and exactly one 16-byte stock policy observation. It contains no native
replacement/removal or reboot action. Only independent acceptance of that linked
evidence can release the original stock–derived–stock RF comparison.

The continuation preparation passed 33 local test methods and 30 independent
record controls. Nineteen retained health, transport, query, UI and observer
lifetime callbacks are unchanged at the AST level. Eight altered configurations
and nine altered partial-run event sequences were rejected. The 27 prepared
control files were reproduced byte-for-byte by a second offline generation.
Four newly authored Python modules passed strict type checking and formatting;
the retained legacy executor is not represented as newly typed code.

Preparation is sealed at
`out/rf/stock-continuation-preparation-20261002T025000Z.toml`, SHA-256
`d0904589216164234a2560d85d028bdb90e3a626766796e7fdc750c3a7c2ca6c`.
Independent readiness review is sealed at
`out/rf/timestamp-continuation-independent-20261002T023800Z.toml`, SHA-256
`9cfcf09a95729c6997b6ce7d51b52c153f43ec8323b00e50945720c7cd863004`.
This is permission to execute the admitted continuation subject to fresh runtime
gates, not evidence that the stock arm has passed them.
