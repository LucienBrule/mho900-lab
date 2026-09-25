# Continuous execution to the next mapped access

Private run `group-continuation-01` validates removing the post-store breakpoint while preserving the two-response
limit and thread observation. The rebuilt observer passed the three [existing controls](guest-group-observer.md)
and two new continuation arms.

Both new arms consume the established two words and store `0x0123456789abcdef`, then execute normally until an
unsupported read at mapping offset `0x4040`. Arm 3 performs that read on the main thread; arm 4 wakes the existing
worker to perform it. Both terminate with exactly two responses and the composed output still intact. Neither
installs a hardware breakpoint or receives a response to the terminal read.

The independent checker verifies the actual ELF instructions, response register deltas, continuous resume,
terminal access attribution, composed state, sibling acknowledgement, one new worker, terminal quiescence and
exact three-thread cleanup in each arm. The old positive breakpoint and two negative guards also pass with this
same executable. Replaying the updated checker against the preceding private and stock captures passes.

Stock Sparrow was absent. Both enforcement samples were `Enforcing`, and all seven system-server samples
agreed. All five executed binary copies match the built observer. The raw evidence index validates, and the guest
was torn down. The [results manifest](../../experiments/group-observer/continuation-results.toml) pins the evidence.

## Scope and next experiment

The continuation mode retains exactly the existing guarded main-thread responses. After response two it uses
continuous resume, captures the next `SIGSEGV` or `SIGBUS`, and classifies the fault address as inside or outside
the existing mapping. It records other signals separately. Unknown events, exits or exhausted bounds remain
negative outcomes. The successful private controls exercise mapped `SIGSEGV` reads, not every fault class or
thread schedule. The success checker deliberately requires a fault inside the mapping, stock/control instruction
binding and complete cleanup; another boundary needs separate adjudication.

Proceed with the byte-identical executable on stock Sparrow, keep the two synthetic words unchanged, and stop
at the next unsupported access. That access has not yet been witnessed by this private experiment. No third value,
physical register semantics, DMA or acquisition model is admitted by these controls.

```sh
tools/guest/build-group-observer.sh
tools/guest/run-admission.sh fresh-continuation-control nextcontrol
kotlin tools/guest/VerifyGroupObserver.main.kts out/guest-admission/fresh-continuation-control
```
