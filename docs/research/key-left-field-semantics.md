# Key.data left field is not a public-serial equality constraint

The [preparation stop](acquired-key-guest-baseline.md) came from a harness
assumption that stock Auklet does not impose in the recovered path. Preserve
the physical public serial and the acquired Key.data left field separately.

In pinned native SHA-256
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`,
`getLicenseKey` assigns field zero to its second output. `verifyLicense`
requires that output to be nonempty (`0x435e7c`–`0x435e84`) and passes it
as the third explicit argument to `verifyOption` (`0x435f08`). There is no
comparison with the public serial along this dataflow.

The verifier stores incoming `x3` at `[sp,+0x110]` at `0x4373ac`. Review of
the complete function (`0x437384`–`0x437bbf`) finds no subsequent load or
address use of that saved argument. Later uses of `x3` load unrelated
logging/memory-call arguments. The incoming string is not dereferenced or
compared by this verifier.

The ordinary installation caller independently corroborates this: `activeOpt`
constructs an empty local RString at `0x438658`–`0x438664`, then passes that
local as the verifier's third argument at `0x438aa0`. Its other occurrences
are destruction paths. It does not fill the local from the public serial or
from Key.data before verification. The cached right-field string at object
offset `0x188` supplies the cryptographic input in both callers.

This is bounded static evidence about these software paths, not an assertion
that every field in every entitlement path is ignored. The left field's
historical or manufacturing meaning remains unknown. Its nonempty startup
gate remains real, and its bytes must be retained. No additional hypothesis
about its format is needed to run the baseline.

Evidence is sealed in `out/overnight/key-left-field-recovery-01`, containing
complete disassembly for the four relevant functions and a review manifest.
The stack-slot search is a cross-check of manual dataflow review, not a
general machine proof of absent data dependencies. No physical connection,
guest execution, installer call or private data mutation occurred.

The corrected disposable fixture will use the public serial from the sealed
physical `*IDN?` response for the modeled public identity, the observed cached
DNA for the modeled DNA response, and the full acquired Key.data unchanged.
It will compare the original parser's two outputs against their respective
decoded fields. The private store remains explicitly fresh and modeled;
the actual specimen's installed option state is still unknown.
