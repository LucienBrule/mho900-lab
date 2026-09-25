# Decision: test the complete missing-device initialization branch

The [static grammar](remaining-initialization-grammar.md) separates four deterministic
SCU/LA stores from intervening transport. Test whether the unchanged stock application
naturally takes the guest's missing-device failure paths and continues to its first
mapped version read. Device absence is a guest hypothesis, not an instrument model.
Preserve the validated ADC452/SPU8 prefix and its two synthetic identity reads.

Choose rotating main-thread hardware breakpoints at exact native call/return PCs.
This preserves continuous execution within libc and between checkpoints. A syscall
observer would introduce additional phase tracking and stops inside unrelated libc
paths without resolving another question in this hypothesis. A kernel facade or native
function substitution would add device behavior that this experiment does not need.

The native checkpoint sequence is fixed:

| Index | Stock PC | Expected evidence |
| ---: | --- | --- |
| 0 | `2955b8` | Board open arguments: literal `/dev/ttyS0`, flags 1 |
| 1 | `2955bc` | Signed low-32-bit open result negative; otherwise stop |
| 2 | `2728e0` | Board result `-1`; saved original bool at `x29-1` is zero |
| 3 | `2ad0b8` | Command is exact `*RST\n`, length 5; live cached descriptor negative |
| 4 | `2ad574` | GPIO open arguments: literal `/dev/hdcode_gpio`, flags `0x802` |
| 5 | `2ad578` | Signed low-32-bit open result negative; otherwise stop before read |
| 6 | `2acfc8` | GPIO helper result `-3` |
| 7 | `2ad120` | Reopen result `-7`, before storing it to cached descriptor |
| 8 | `2ad6ec` | Command result `-3` |
| 9 | `2728ec` | Reset result `-1`; cached descriptor `-7`; LA shadow still zero |

The first two SCU stores precede these checkpoints, using live shadow checkpoint
`0x80000000` and then zero at offset `0x4004`. Checkpoint 0 must not be satisfied before
both stores. After checkpoint 9, permit only `W7034:1,0`, with live LA shadow checks,
then stop at the uncompleted main-thread mapped `R32(4)`. The proposed successful
prefix therefore contains 464 accepted stores, ten checkpoints and only the two
previously admitted read responses. The later DAC candidate is outside this run.

Validate stock function/data bindings, literals, instruction bytes and live state
before completing the relevant phase. Do not replace an unexpected descriptor, branch,
shadow or return value. Preserve all general registers at breakpoint stops; only the
four admitted mapped-store completions advance PC, with all other state unchanged.
Never single-step through library code or synchronization sequences.

Hardware debug state belongs to a traced thread. Replace one slot only while the main
thread is stopped; clear the old slot, read back, install the next and read back again.
Private controls must establish the guest's actual rearming behavior. Check main TID,
trap code, target PC and opcode on every hit. Maintain existing group coverage; any new
clone during the new region is a terminal outcome after safely registering it for
cleanup. Existing prefix clones retain their previously validated handling. Other
threads do not satisfy main-thread checkpoints. Quiesce the entire known group at every
terminal outcome, not at every ordinary checkpoint.

This does not provide process-wide UART tracing. Other threads' mapped accesses remain
observable through the protected mapping and existing group observer; their unrelated
transport is outside this hypothesis. No stock code bytes are replaced. A successful
open, cached nonnegative descriptor, true initialization branch, mismatched state,
unknown access, unexpected trap, process exit or deadline is a valid negative result.
Do not alter guest device nodes to force the missing-device branch.

Private controls precede stock execution. They must cover the complete branch, atomic
completion between rotating checkpoints, successful opens stopping before I/O, cached
and bool divergence, shadow/binding/operand/width/order/thread mismatches, omitted or
reordered checkpoints, repeated old breakpoint detection, deadline cleanup and group
coverage. Preserve and rerun the existing ADC/SPU regression controls with the new
executable. Independently verify raw evidence; a verifier should not accept the
observer's declared match without checking recorded fields.

Admit three tasks: implement and privately validate this bounded observer; perform one
fresh stock falsification with exactly that executable; evaluate the observed branch
and next dependency. Commit and push this tasking before implementation, the private
conclusion before stock execution, and the stock conclusion before any successor run.
No GPIO, UART, mapped-version or acquisition response is introduced by this batch.
