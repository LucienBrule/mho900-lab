# ADC capture final-health routing decision

The accepted private controls exposed a runner omission: the shared final-health
mode list excludes both new capture modes. Private-helper health records are
complete, but the stock profile requires the generic records too. Starting the
unexecuted stock freeze would predictably fail its evidence requirements.

The selected continuation is a narrow orchestration repair. Add the two modes to
the existing dispatch, exercise the new routes on host success and failure paths,
and freeze an updated stock contract and verifier. Preserve the original freeze
and private result; do not repeat the native controls or change their conclusion.
The native capture binary and hardware response model remain the accepted ones.

The admitted batch contains the repair and an explicit evaluation gate. The stock
task gains that gate as a prerequisite. No guest runs during implementation; a
stock run follows only an accepted, pushed gate and the existing free-space check.
The broader initialization architecture is unchanged: this corrects missing
health evidence before the planned bulk software-input observation.

## Repair verification

The dispatch now includes both new modes. Seven host cases passed for each of
`loadermodel`, `adcinputcontrol`, and `adcinputmodel`: normal completion, mandatory
collection failure, optional collection failure, early abort, final-health failure,
and index failure paths. Each booted case attempts health exactly once; cleanup
runs exactly once, and failed mandatory collection prevents admission.

The revised full stock checker accepts an independent synthetic positive fixture
and rejects an independently copied fixture containing the old runtime, even with
a regenerated evidence index. Native source, capture header, binary, capture
checker, and stock artifact identities are unchanged. No guest was launched for
this repair. The original unexecuted stock manifest is retained as
`stock-initial-inputs.toml`; `stock-inputs.toml` revision 2 binds the corrected
runtime, revised task contract, and accepted private result.

Reproduce the dispatch controls with fresh directories:

```sh
sh tools/guest/test-admission-runtime.sh out/health-loader loadermodel
sh tools/guest/test-admission-runtime.sh out/health-private adcinputcontrol
sh tools/guest/test-admission-runtime.sh out/health-stock adcinputmodel
```

## Admission evaluation

The gate admits one stock capture using freeze revision 2. All eleven original
native controls remain accepted; the repair changes only final-health routing,
its host tests, and the corresponding stock verification pins. The preboot disk
check still runs at execution time, and the selected run directory is unused.
There are no new synthetic device responses and no execution past `0x333ba8`.
Unexpected pointers, incomplete evidence, or changed state close the actual
question as a negative result. No adaptive retry is included.
