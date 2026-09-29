# Stock native entitlement baseline

The first guest execution loaded unchanged specimen-derived Auklet and its packaged dependencies successfully.
`CApiFactory::Api_Create` then raised an access violation at address zero. The run stopped there. It did not reach
the intended DNA observation point, service inventory, initialized identity, or an option query. This is an
earlier component-environment failure, not a dynamically validated DNA failure or an entitlement result.

Run `baseline-02` used the pinned API-25 ARM64 Android image, fresh independent userdata, the established empty
`/rigol` ramdisk derivative, and a userdata-backed bind mount containing copied vendor/key files. All three
library hashes were checked before launch and their guest round-trip copies compared byte-for-byte. The original
accession, stock APK and stock native files were not modified. No physical instrument contact occurred.

The new runner confines its emulator, dedicated ADB server and Frida controller to loopback with a child-only
macOS sandbox profile. Host controls demonstrated allowed loopback TCP, denied alternate-loopback TCP/UDP and
inheritance through fork/setsid; an allow-all negative profile failed the control. `ADB_MDNS=0` was checked against
the installed binary: `mdns check` returned `ERROR: mdns discovery disabled` before guest launch. The USB-only
`--one-device` flag is not treated as a network-discovery barrier. No global host policy was changed.

## Observations

| Question | Result |
| --- | --- |
| Actual Android linker loads C++, FFTW and Auklet | All three returned successfully |
| Pinned native helper instruction prefixes | Both matched |
| Stock service factory | Null-address access violation |
| Factory completion / service inventory | Not reached |
| Runtime DNA boundary | Not reached |
| Model, capabilities, option state | Unavailable; no values invented |
| Copied `/rigol` files before/after | Same paths, modes, sizes and SHA-256 hashes |
| Guest `system_server` | Same PID before and after |
| Guest SELinux | Enforcing before and after; policy bytes separately retained |
| Install / process-reload / reboot persistence | Not attempted |

Frida's own guest instrumentation policy change remains the previously documented experimental limitation.
The component was a fresh native sleep process, not Sparrow's Java application. Loading Auklet through that
process proves native-loader viability; it does not prove complete application initialization.

The controller reported failure, not success: zero dependency-stop events, one native-call error, runner exit 3.
Its native-call exception mode converted the fault into a JavaScript exception without preserving the precise
native PC in the recorded message. That diagnostic loss is the next useful correction. The next question is
which concrete caller/environment prerequisite the stock factory requires, not whether changing an option token
can somehow make this baseline work.

## Reproduction and evidence

`prepare-entitlement-fixture.py` selects fixed archive members into a fresh private directory; it does not extract
arbitrary archive paths. Python supplies tar/ZIP support and the upstream Frida client API. The injected native
call observer is JavaScript because it executes through Frida. Shell handles emulator process orchestration.
Use configured SDK and Frida locations; proprietary archives and per-unit manifests remain local.

```sh
tools/guest/run-entitlement-baseline.sh RUN_ID PRIVATE_FIXTURE \
  tools/guest/entitlement-controller.py tools/guest/entitlement-baseline.js
```

Private run: `out/specimen-entitlement/baseline-02`. The public result manifest pins the controller transcript,
result and evidence index. The runner retained its source snapshot, guest logs, file manifests and policy files.
It stopped the experiment process, emulator and dedicated ADB server after capture.

`baseline-01` was a host-only preflight failure: a restrictive umask changed copy permissions while all bytes
remained equal. No ADB server or guest started in that attempt. The copy now preserves permissions; the original
diagnostic directory remains separate. It is not counted as a native execution.
