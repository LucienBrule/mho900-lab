# Staged emulation plan

2026-09-24. Proposed work only; the first engineering task has not been executed.

## First executable task: capture the stock APK's first failure

**Transition:** from a hash-identified stock APK with no runtime witness to a reproducible ARM64 Android 7.1/API-25
installation/launch result, including a precisely classified failure if launch is blocked.

Start with unmodified `firmware/app/Sparrow.apk` from the normalized `.26` tree. Preserve its signature and archive
bytes. No capability patch, manifest edit, re-signing, fabricated model identity, or synthetic devices in this run.

1. Verify ZIP/APK/ELF hashes against [the inventory](observed-inputs.toml). Record tool versions and host details.
2. Identify and pin an obtainable ARM64/API-25 image and compatible emulator/runtime. Verify this pairing rather
   than assuming the current Android emulator supports it. Record origin, hashes, kernel, Bionic, page size,
   renderer, platform signing certificate, and available debug privileges.
3. Boot an isolated disposable guest and witness API 25, ARM64 ABI, boot completion, and working graphics/ADB.
   Record its baseline logs before installing anything. Do not connect to a physical instrument.
4. Attempt ordinary installation of the byte-identical APK. Capture package-manager output and relevant logs.
   Its system shared UID may reject a generic platform certificate; do not hide or work around that first result.
5. If installation succeeds, launch `com.rigol.scope/.SplashActivity`. Capture full logcat, exit/crash information,
   tombstones when accessible, process state, screenshot, and the selected model/capability if queryable.
6. Repeat from a fresh guest state to establish reproducibility. Record a wall-clock timeout for boot/install/run;
   distinguish timeout, crash, install rejection, stable splash screen, and stable useful UI.

**Acceptance:** exact inputs/environment, commands, raw evidence hashes, repeated outcome, and the earliest
evidence-backed blocker. If no compatible guest can be obtained, deliver a concrete environment feasibility
blocker with tested availability/runtime constraints; do not present that as a completed application launch.
A working UI requires responsiveness and sustained useful state, not merely a screenshot or a surviving process.

**Current host observation:** macOS ARM64; Kotlin/Gradle commands, Android SDK build-tools, platform-tools and
emulator files are present. The only installed system-image directory is API 37.0, ARM64, Google Play, 16 KiB.
No API-25 guest was found in that SDK inventory. No guest was booted and no additional tools were installed.
This inventory does not establish that the available commands or images are suitable for the target experiment.

The initial task should include a small reproducible runner and evidence capture, preferably Gradle/Kotlin for
semantic operations with shell only where host integration is clearer. Add a fast documentation/manifest check
when build tooling is introduced; keep CI independent of private inputs. Admit an atomic taskctl contract after
authorization, with explicit acceptance and receipt evidence. Do not seed the entire speculative roadmap now.

## Escalation by observed dependency

Stages below are conditional. Preserve the unmodified baseline result and change one stated assumption at a time.
Each run gets an immutable input/fixture/environment manifest and a fresh writable overlay.

### 1. Environment and signing compatibility

If installation fails on shared UID or certificate compatibility, record the exact error and guest platform
certificate. Assess a compatible vendor environment or a deliberately modified research guest. Keep the APK
byte-identical. Any guest package-manager compatibility change is a separate, labeled experiment with its own
environment hash; it cannot be described as a stock Android result. Do not change host security configuration.

If ARM64/API-25 execution itself is unavailable, assess a pinned older emulator, AOSP guest build, or suitable
isolated Linux execution host. A newer Android version is a separate control experiment, not the requested baseline.
Do not begin RK3399 board emulation merely because the first image candidate fails.

### 2. Minimal filesystem reconstruction

Trigger: a witnessed missing path, configuration, service dependency, or data error after install/launch.
Supply only necessary stock `.26` resources in a guest overlay, preserving source hashes and guest paths.
Keep calibration defaults separate from measured per-unit calibration. Snapshot writes, including vendor recovery.
Success: the same startup proceeds beyond the identified dependency; unrelated errors remain visible.

### 3. System properties and identity

Trigger: logs or a traced reader establishes a required property/value or identity input.
Build versioned typed fixtures; record each property's source and rationale. Do not infer an MHO984 model selection
from `ro.product.model`: the prior native analysis identifies encoded vendor item 5 as the scope-model input.
Represent missing identity honestly; verify fallback behavior before designing a synthetic identity provider.
Success: the exact property/identity read is satisfied and the native model/capability outputs are recorded.

### 4. Native dependency interception

Trigger: concrete native load/init failure or a hardware-facing call that cannot yet run.
Retain the real Sparrow/JNI/native libraries. Trace narrow boundaries, including fortified libc entry points and
possible direct syscalls; do not assume `LD_PRELOAD` works through Android's process launcher or linker policy.
Record every modeled call, return, error, side effect, and unsupported operation. Return useful failures first.
Success: a reproducible next boundary with an explicit list of substituted behavior.

### 5. Fake FPGA control mapping

Trigger: startup reaches the observed 16 MiB bypass mapping and register accesses.
Choose trapped MMIO or a verified native register-function boundary based on coverage evidence. A zero-filled
file is a diagnostic experiment only. Recover the minimum ID/status/reset/ready state machine and implement it
with deterministic event ordering. Trace offsets, widths, values, read side effects, and timeouts.
Success: repeatable initialization through the targeted control sequence, including deliberate negative cases.

### 6. Fake DMA

Trigger: an identified stream read or `dma_auklet` operation blocks progress.
Treat XDMA C2H and the separate 256 MiB DMA mapping independently. Recover ioctl payloads, buffer limits, address
units, transfer sizes, completion semantics, and ownership before creating data. Preserve short reads, errors,
timeouts, and backpressure. A control-register trace alone cannot specify this backend.
Success: one reproducible transfer plus boundary/error behavior, with no unexplained successful operations.

### 7. Synthetic acquisition

Trigger: a defined transfer format reaches the actual application consumer.
Inject deterministic zero, impulse, ramp, and sine fixtures with explicit channel packing, sample rate, scaling,
trigger position, and calibration assumptions. Check numeric results where accessible as well as real UI rendering.
Success: the same fixture produces the expected waveform/results repeatedly. This establishes a software path,
not analog bandwidth, calibration accuracy, or real-time performance on an instrument.

### 8. Stock, D-model, and minimal-patch regression

Trigger: the stock MHO984 state and acquisition path are repeatable and subsequent patch work is authorized.
Keep environment, traces, calibration fixture, and acquisition inputs constant. Compare unmodified MHO984,
unmodified D-record behavior where reconstructable, and the identity-preserving MHO984 capability redirect.
An injected model-record result is a partial D-model reconstruction, not a full MHO984D instrument.

Measure identity, selected bandwidth, option handling, filter choice, delay outputs, register sequences, and
rendered/numeric acquisition results. Preserve expected capability-driven changes in an explicit delta ledger.
Use prior bounded tests as a separate regression tier, retaining their stubs and limits. Do not silently replace
the stock policy with NK behavior. Reset call-once state and cached configuration between cases.

### 9. Replay and physical validation

When hardware arrives, acquire traces and per-unit facts under a separately authorized device procedure.
Replay must enforce operation ordering and report divergences, not just return a prerecorded success stream.
Run the same meaningful behavioral tests across emulated, replay, and real backends; mark unsupported capabilities
explicitly. Physical measurements remain a separate evidence class and can falsify the emulator's assumptions.
