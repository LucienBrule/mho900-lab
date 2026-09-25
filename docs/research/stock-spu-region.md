# Stock SPU region result

Stock Sparrow matched the complete eight-write SPU prediction after the previously
validated 452-write ADC prefix. The next access was an uncompleted main-thread W32 at
offset `0x4004`, value `0x80000000`, stock PC `0x27043c`, instruction `0xb9000109`.
This agrees with the statically recovered first SCU initialization write. No new returned
register value or device side effect was introduced.

Run `stock-spu-region-01` used the exact native executable tested by the
[private controls](spu-transcript-controls.md), SHA-256
`ac86c83927a0bba752491c388e371d811d7bce9013007a51d2568837659311ae`.
The fixed ADC and SPU input hashes matched before execution. Frozen independent evidence
verification passed, including unchanged stock APK/library bytes and admission preservation.

## Prediction and observation

| Question | Observed result |
| --- | --- |
| SPU function and shadow bindings | All fifteen expected targets matched. |
| Series selection | Both captures matched domain 8, series 900, power-mode 0 and all nine normalized records; record 2 selected the 16-record table. |
| Independent gain/range selections | Sample records 0, 1 and 15 matched; gain mode 1 and range mode 4. |
| Checkpoint shadows | Control 1 after the first bit-set; gain, TX and ADC-control zero. |
| Complete SPU sequence | `W1000: 1,0,0,0x10,0`; `W105c: 0x55555555`; `W1010: 0x20000000`; `W1014: 0x00f00001`. |
| Terminal shadows | Control 0, gain `0x55555555`, TX `0x20000000`, ADC-control `0x00f00001`. |
| Subsequent boundary | `W4004: 0x80000000`, left uncompleted. |

Every accepted store retained all non-PC registers. The two existing synthetic DNA reads
still produced stock software identity `0x0123456789abcdef`. ADC bindings, table data,
initializer words and shadows were independently checked again; all 460 accepted writes
matched their ordered candidates without adaptation.

The observer covered 22 initial threads and one runtime clone. All 23 terminal threads
were quiesced and exactly reaped. `system_server` remained PID 1093 and enforcement stayed
enabled. Dedicated guest services were stopped. The composite snapshot command returned
zero in this run; three separate snapshot commands also succeeded and 994 mapping rows
were verified.

## Interpretation

This is a successful whole-subsystem falsification test: static recovery predicted the
software-selected operands, and stock execution agreed under checked live inputs. The
live records for the two selectors are now observed independently rather than inferred from image defaults.
The first subsequent access supplies a concrete checkpoint for the remaining initialization
region.

The result establishes synthetic write acceptance and stock software state, not FPGA
configuration success, physical identity, readiness, acquisition, or a useful UI. Equal
non-atomic snapshots do not exclude intervening change and restoration. The next offset
is consistent with SCU initialization; this observer does not record a complete internal
function-call trace or UART/MCU transport behavior. Those paths remain inputs to the next
decision, rather than an implicit extension of this experiment.

The [result manifest](../../experiments/spu-transcript/stock-results.toml) pins the raw
capture, frozen verifier output and harness changes.
