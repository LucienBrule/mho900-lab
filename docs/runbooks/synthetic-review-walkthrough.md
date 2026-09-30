# Reproduce a review without an instrument

This example uses only the tracked [synthetic fixture](../../examples/sealed-review/).
Every packet, counter, timestamp and identity string is manufactured. No network
interface, device, endpoint, recorder process or private acquisition is needed.

From the repository root, choose an output directory that does not exist:

```sh
uv sync --locked --all-packages
mkdir -p out/tooling
uv run --locked sh examples/sealed-review/walkthrough.sh out/tooling/synthetic-review-01
```

The script refuses an existing output directory and retains any failure evidence.
It invokes the public `mho-lab` executable already on the uv environment's PATH.
An installed-wheel consumer can run the same script with that environment's
`mho-lab` on PATH; uv is not used inside the script.

The resulting files show three different questions:

| Report | Expected result | What it establishes |
| --- | --- | --- |
| `accepted.toml` | accepted; six files, six frames, two queries | The supplied synthetic inventory, counters, captured stream and separate transcript bytes agree |
| `changed.toml` | rejected at `inventory-before` | Changing a response from `1` to `0` breaks the original seal |
| `mixed.toml` | rejected at `transcripts` with `tcp-transcript-mismatch` | Resealing that changed response does not make it agree with the unchanged capture |

The original copied tree remains in `accepted-run/`. The second tree is
`changed-run/`. Both manifests, the role profile, seal logs and reports are outside
those trees. The synthetic identity remains redacted in reports; the option
observation shows selector `FLEX` and state `1` on acceptance.

The first review uses the fixed expected manifest pin:

```text
b049d958172b0b013aa9934c66e029d2a33559e13aed9d3e362719e8ce9672f6
```

The script also byte-compares the newly generated seal with the tracked manifest.
For the deliberately changed tree, it uses the digest emitted by its new seal
operation. That latter digest describes new synthetic bytes; it is not a substitute
for a previously preserved pin when reviewing historical evidence.

To inspect the exact commands, read
[walkthrough.sh](../../examples/sealed-review/walkthrough.sh). Its sequence is
`evidence seal`, `review inspect`, one local copied-file edit, another review,
then a separate seal and review. The two expected rejection exit codes are checked;
unexpected command failures stop the example. Nothing is silently overwritten.

Acceptance is intentionally narrow. The manufactured counter file cannot prove a
recorder stopped gracefully or that drop counters were supported. Matching bytes
cannot prove physical origin, complete wire observation, response causality,
device execution or option persistence. The report explicitly marks its supported
proof flags false; it makes no persistence claim. See [sealed offline review](sealed-offline-review.md) for the full contract.
