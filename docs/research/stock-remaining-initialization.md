# Stock SCU, transport and LA initialization

The fresh `stock-remaining-init-01` run matched the complete predicted region: 464
ordered stores, ten native checkpoints and then the uncompleted main-thread `R32(4)`.
The executable was identical to the one cleared by the
[private rearm controls](remaining-init-rearm-controls.md). The stock APK and native
library remained unchanged. This is a guest observation under the two previously
admitted synthetic identity words, not physical FPGA validation.

The accepted prefix contains 452 ADC stores, eight SPU stores, two SCU stores at
`0x4004` (`0x80000000`, `0`) and two LA stores at `0x7034` (`1`, `0`). The ten
[preselected call/return checkpoints](remaining-init-decision.md) all matched their
arguments, instruction bindings and live-state guards. Board open failed, board init
returned `-1`, the saved initialization bool was false, and the cached command descriptor
was negative. GPIO open failed; its helper returned `-3`, reopen returned `-7`, command
returned `-3`, and reset returned `-1`. The cached descriptor became `-7`. The parent
continued to the LA initialization and mapped version query, as statically predicted.

The boundary is a four-byte read at mapping offset `0x4`, stock-relative PC `0x270604`,
opcode `0xb9400109`. It was left uncompleted. No version, UART, GPIO, DDR or additional
identity response was supplied. Terminal SCU and LA shadows were zero. No useful UI or
acquisition behavior is established by this result.

The frozen independent verifier checked every modeled access, native checkpoint,
register-preservation obligation, breakpoint clear/rearm transition and final group
cleanup. All 21 initially observed threads plus one prefix clone were quiesced and
exactly reaped. No new clone appeared in the added region. The three recorded
`system_server` samples remained PID 1055, enforcement stayed enabled, and dedicated
guest services were stopped. The source snapshot, pinned executable, original APK and
library hashes were independently checked. The evidence index covers 182 artifacts.

These are main-thread transport checkpoints, not a process-wide UART trace. Other
threads remain covered at the protected mapping; unrelated transport is outside the
observation. The native summary's private-only I/O and atomic counters are inactive in
stock mode and must not be interpreted as stock I/O absence or stock atomic counts.
Live mutable-state observations also do not imply an atomic process-wide snapshot.

Reproduce with the pinned local prerequisites using:

```sh
ANDROID_SDK_ROOT="$ANDROID_SDK_ROOT" tools/guest/run-admission.sh NEW_RUN_ID remainingmodel
kotlin out/guest-admission/NEW_RUN_ID/source/VerifyRemainingObserver.main.kts \
  out/guest-admission/NEW_RUN_ID remaining-stock
```

The [result manifest](../../experiments/remaining-init/stock-results.toml) pins the
capture, frozen verifier, independent preservation review and source wiring. The next
decision should use static recovery of the version/DAC/DDR initialization tail and its
returned-state dependencies. There is no reason to rediscover its deterministic stores
one at a time.
