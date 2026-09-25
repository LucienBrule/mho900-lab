# Two-word composition experiment

The first run stopped in a private control before supplying any stock device response. Its first single-step
advanced PC by four bytes and reported `SIGTRAP` with code 4. The observer required code 2 and rejected the stop.
The stock two-word composition and global store therefore remain unobserved dynamically.

This experiment tests the [statically decoded composition](xdma-identity-flow.md) in a disposable Android guest.
The stock oscilloscope APK and native library remain byte-identical. The device model supplies two explicit
synthetic register words; no physical instrument is accessed and no physical identity is inferred.

## Question and fixture

Does the observed main thread assemble these two words, apply the predicted mask, and store the result in
`CApiUtility::m_DNA` before entering `ApiUtility_ConvertDNA2Key`?

| Access | Synthetic response |
| --- | --- |
| read32 at mapped offset `0x4048` | `0xe1234567` |
| read32 at mapped offset `0x4044` | `0x89abcdef` |

The predicted result is `0x0123456789abcdef`: the first response contributes its low 25 bits as the high word,
and the second contributes all 32 low bits. Distinct words and set bits above the mask make word order and masking
observable. [fixture.toml](../../experiments/xdma-two-word/fixture.toml) records the exact constants and boundaries.

## Observation method

The external native supervisor retains the protected 16 MiB mapping and exact stock accessor guard from the
[single-read experiment](xdma-single-read.md). It completes at most two read32 instructions, in the specified
order, by setting W9 and advancing PC four bytes. It verifies the resulting register state. Stock instruction
bytes are never changed.

After the second response, the supervisor single-steps with a fixed 256-instruction budget. It records each
instruction and stop. An unexpected signal or exhausted budget terminates the observation. At stock ELF address
`0x42a8ec`, it records the source register and destination of the global store, then reads the destination after
that instruction. The target stop is `0x42a2b4`, before the call to the converter executes on the observed thread.
The GOT slot at `0xb8d758` must resolve to the stock global object at `0xbbccf0`, both adjusted by the load bias.

At the target boundary, the supervisor records the global value and kills the observed process while it is
stopped, then waits for termination. It does not resume the converter call. The verifier checks the instruction
sequence against the stock ELF and captured guest libc; the accessor's return path includes `pthread_mutex_unlock`.

Before stock responses are enabled, four private controls cover 32/64-bit reads and writes. A fifth control
completes both words and steps through assembly, masking and storage to a named stop. A sixth requests `0x4040`
as its second access and must be rejected after only one response. The private controls do not call stock code.

## Scope

The intended stock observation covers the traced main thread. Other application threads would remain untraced.
The implementation captures a thread inventory and store witnesses when that phase is reached; this run did not
reach it. Such store witnesses would not prove the absence of concurrent writes elsewhere in the application.

The guest retains the previously documented, scoped APK admission and process-label fixtures. Their guest policy
effects remain part of the experiment. No host policy changes or global disabling of guest enforcement are used.
The synthetic values establish no physical FPGA identity, acquisition behavior, register timing, DMA or interrupt
semantics. Conversion-helper behavior and later consumers remain outside this run's intended boundary.

## Observed result and decision

Run `two-word-01` passed all four width/direction controls. The next private control completed its reads at
`0x4048` and `0x4044` with the specified words. Its first stepped instruction was `bfi x9, x11, #32, #32`,
opcode `b3607d69`, at helper PC `0x211784`. The kernel then reported PC and signal address `0x211788`,
signal 5, code 4. The supervisor emitted `step-rejected`, killed the control, observed termination status 9,
and returned 73. Neither masking nor storage was observed. The unexpected-second-access control was not reached.

The shell's control gate stopped before attaching the stock observer or creating its guest device alias.
Sparrow remained at SplashActivity, PID 2512, until guest teardown. Its installed APK and extracted native-library
hashes match the stock inputs. The admission verifier passed, including all three admission rejection controls;
`system_server` remained PID 1045 across all three samples. Guest teardown completed and the experiment ports
have no listeners. The outer run reports inspection completed because it separately records the native helper's
exit status; that outer status is not evidence that the composition test succeeded.

The guest reports Linux `3.18.91+`. In the upstream Linux v3.18 ARM64 reference, `single_step_handler` assigns
`TRAP_HWBKPT`; the corresponding signal header defines its low code as 4. This agrees with the observed stop
and identifies the observer's code-2 requirement as an unsupported assumption for this guest. The reference is
pinned to commit `b2776bf7149bddd1f4161f14f79520f17fc1d71d`; it is not a verified source match for the guest binary.
See the pinned [handler][handler] and [signal definitions][signals].

[handler]: https://github.com/torvalds/linux/blob/v3.18/arch/arm64/kernel/debug-monitors.c#L227
[signals]: https://github.com/torvalds/linux/blob/v3.18/include/uapi/asm-generic/siginfo.h#L215

Close this attempt as a negative observer-control result. Preserve its runtime sources and raw capture unchanged.
The successor question is whether a pinned guest profile expecting code 4 passes the complete private step and
rejection controls, then reaches the original stock stop within the same 256-step limit. That needs a separately
admitted batch. Do not broaden acceptance to arbitrary traps or remove the instruction, PC and termination checks.

The independent post-run verifier explicitly checks this negative outcome; its added `step-rejected` mode was
written after the run. It is distinct from the original source snapshot. A copied fixture with the recorded
code changed to 2 is rejected. The [results manifest](../../experiments/xdma-two-word/results.toml) pins both
verifier versions, the raw index, probe ELF, reference files and verification output.

## Reproduction

Configure the local LLVM compiler/linker and Android SDK as described by the existing guest harness, then run:

```sh
tools/guest/build-native-probe.sh
NATIVE_TWO_WORD=1 tools/guest/run-admission.sh fresh-run-id native
kotlin tools/guest/VerifyPairControls.main.kts out/guest-admission/fresh-run-id
kotlin tools/guest/VerifyNative.main.kts out/guest-admission/fresh-run-id two-word
```

Use a fresh run ID. A verifier rejection must be investigated as evidence; it is not permission to repeat the
experiment with relaxed conditions. Raw guest files and proprietary inputs remain in ignored local directories.

Verify the preserved negative result without starting a guest:

```sh
kotlin tools/guest/VerifyLabeling.main.kts out/guest-admission/two-word-01
kotlin tools/guest/VerifyPairControls.main.kts out/guest-admission/two-word-01 step-rejected
```
