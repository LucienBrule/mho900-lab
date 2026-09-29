# Permanent licenses and older saved-time state

The complete acquired catalog installed ten permanent licenses and retained them
through component restart and guest reboot. Each ordinary installation changed
only saved-time record 16192 in the modeled private stream; the per-option
attempt/trial records were unnecessary for those successful permanent installs.
The previous reloads used post-install private bytes. They therefore do not
answer whether the saved-time update itself is needed for later acceptance.

This separate contrast keeps all ten accepted license files, the acquired key,
all witnesses, stock native code and the ART host. It replaces only
`model/private.mem` with the exact pre-install stream retained immediately before
the final BWU03T08 installation. The positive control is the accepted complete
stock reload. Preparation must show that the two private streams differ only
in record 16192, with key backup 2337 unchanged.

The source catalog seal is
`0724e39fbfb4e2d320b2c4c48d6243f8b566d63a47d2049ab7fb9f1118758781`;
the accepted stock-control seal is
`7ffb39a50f36e97c9fce32e72869b7d3698b2aa869fbb83d10992a061c36101f`.
Both inputs are verified before constructing the contrast. A separate preparation
mode and independent provenance wrapper bind the older stream, while retaining
the unchanged complete-catalog guest program and verifier.

The experiment runs one fresh-process reload. It must observe the original
consumer accept all ten licenses, all thirteen expected catalog entries true,
BND false, public MHO984 identity and raw/effective bandwidth enum 17. There is
no installer, token producer, private formatting or physical instrument access.
All 22 canonical files must remain unchanged during execution.

A positive result would establish that this older saved-time stream does not
prevent permanent-license acceptance during component initialization. It would
not establish full `License.start`, physical filesystem durability, asynchronous
FRAM saving, a live installation or reboot persistence on the instrument. The
existing guest reboot evidence and this one-file state contrast answer different
questions.

## Preparation and lifecycle boundary

Both source seals and all four source/control phases were independently verified.
The resulting fixture changes exactly one canonical file. Nine wrong-scope,
wrong-source, wrong-control, wrong-profile and wrong-private-state controls were
rejected; the independent wrapper also rejected seven invalid profiles. Python
and shell syntax checks passed. Preparation seal: `5cf54ba741bca9cc21686fce5dd9cfd5b9e6e824e6ccb55ba9dd9bf7d521647c`.

A separate static check compared all216 instructions in `License.start`,
`GetSavedCurrentSysTime`, `SaveCurrentSysTime` and `UpdateLeftDays` against the
pinned stock ELF load segments. `start` at `0x43612c` conditionally processes
positive elapsed time, saves current time and requests300000/60000ms timers.
`UpdateLeftDays` branches around adjustment for license time below2 or above6;
permanent time0 skips that body. `SaveCurrentSysTime` writes8bytes under private
record16192. Static evidence seal:
`8861f52c63241e9c89235fef8f3d5265b9d93ac3ec376d2bbbc06692c1a85bc5`.

These static branches explain why the older saved-time contrast is narrow.
They do not prove that timers, full application startup or physical saving have
executed. No timer or event-loop model was added.

## Result: older saved-time state accepted

Run `acquired-stale-private-01` completed 2026-09-29 14:46:26–14:46:44 UTC.
All ten permanent licenses passed original initialization consumers through
thirty observed AES blocks. Four absent-license consumers returned false; the
actual catalog still reported thirteen true entries and BND false. Public model
remained MHO984 with raw/effective enum17 before and after original option policy.

There were no installer or token-producer calls. All21 other canonical files
matched the accepted stock control, and the exact older private stream remained
unchanged before and after execution. Native bytes and guest template also
matched that control. The1,035 journal records were reconciled through terminal
acknowledgment; within-boot health and policy checks passed.

Independent review rejoined original consumer decode/key/cipher/plaintext
evidence and verified all281 sealed artifacts. Run seal:
`4e06f50571f0f526dcb6affdb5ecf212ae729dde184173eef58cd3277a61cdfd`.

The specific older saved-time record does not prevent these permanent files
from validating during component initialization. This does not show that time
state is irrelevant to every license type, full startup or physical persistence.
No reboot was needed for this one-file contrast; earlier guest-reboot evidence
remains separately scoped to its own post-install fixtures.

## Decision

The exact older saved-time stream is sufficient for the observed permanent-license
initialization path. Further repetitions of this same component test would not
resolve full application lifecycle or physical storage durability. The
[current checkpoint](specimen-entitlement-checkpoint.md) records the next concrete
bench questions: a defensible private-state baseline and one ordinary non-bundle
installation/reboot observation. No physical mutation or new guest run is admitted
by this decision.
