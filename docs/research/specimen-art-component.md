# Stock API under an ART component host

The native-only factory fault proves that its notification path needs a Java VM. The candidate correction uses
`app_process64`, an inert project-authored Java main, and the unchanged specimen APK on its classpath. The original
API static initializer performs `System.loadLibrary`; stock `JNI_OnLoad` registers its real class and methods.
No native constructor, option result, Java callback or application class is replaced.

The specimen APK and official `.26` match. Targeted decompilation confirms that original `API.UI_Redraw` delegates
to MessageBus, whose initial queue mode does not need a Context, Activity or Looper. This supports a component
experiment without invoking `UI_StartBusiness`, which would also enter broad hardware initialization. It does not
establish that error presentation or the full Sparrow application can run without their Android context.

## Readiness control 1: runtime-start race

`art-readiness-01` ended before API loading or factory execution. ART reported
`Check failed: runtime->IsStarted()` while the instrumentation thread attempted attachment and the main thread
was still in `Runtime::Start`. A visible VM is therefore insufficient proof that attachment is ready.

This is a loader-control failure, not evidence about the stock license service. The correction is an explicit
controller gate on the inert Java main's stdout readiness marker before loading the Java observer. The existing
host main emits that marker after entering Java code; no stock class initialization is needed for the marker.
The admitted component task still has its single stock run pending after loader readiness passes.

The negative run is preserved separately, with unchanged before/after copied instrument files and no physical
contact. Runner exit was 3. No option query, installation, capability selection or hardware response occurred.

| Artifact under `out/specimen-entitlement/art-readiness-01` | SHA-256 |
| --- | --- |
| `guest-events.jsonl` | `b5d61659ff2d35eff802048a340ba89e90e096a6516fc39687ab8800d2b9ae01` |
| `evidence-sha256.txt` | `c4758d3ec40979c249a3eab49d3f69882cd23a28cded447512a40d0ad8cc9447` |
| `logcat-final.txt` | `c6c66304e0791e4138f4fe7cd7e20d10459f6182d54bb3d83e430ac406d07251` |

## Readiness control 2: Java caller context

`art-readiness-02` passed the Java-main marker gate. It then stopped before API class initialization: directly
calling `System.load` through the instrumentation bridge threw a null-caller-class exception. The original
API class had not run and the factory remained uncalled. This distinguishes a bridge caller-context problem
from a stock library initialization failure.

The pinned Auklet ELF declares both packaged support libraries in `DT_NEEDED`. The next loader control can
therefore omit the unnecessary direct preloads and let the original API static initializer call
`System.loadLibrary` from its genuine Java caller, using the configured native-library search path. No library
or stock Java bytecode change is required.

The preserved guest journal SHA-256 is `60e306d5ee413959e4221b73f342b8f7c0aaf27f395633ace9a495dd154e2f18`;
the evidence index is `97b1e9269ea047620bbfe1c70fca259afa23fbfcce14845526b14ce25a462a1c`.
Runner exit was 3. This remains readiness preparation; the admitted stock factory trial has not begun.

## Readiness control 3: passed

`art-readiness-03` passed at 06:16:02 UTC. The original API initializer loaded all three native libraries from
the pinned fixture paths. Stock JNI registration populated the real VM, class global, redraw and error method
references. Calling stock `_JavaVM::GetEnv` on the attached thread returned zero and a nonnull environment.
No callback substitution or factory call occurred. All 13 journal events match the host record, the terminal
was durably acknowledged, and the runner returned zero. Copied instrument files remained unchanged.

Journal SHA-256: `fee345aebc1344f65469e0aa81be0694e86abb8fbe8de22342f8057150b5e77f`.
Evidence-index SHA-256: `d30e16cc09f762a3fabf096faa83cd0e537e157dac170a4f59cf4c70a110ff0b`.
The single stock factory trial can now proceed in a fresh guest using this caller contract.
