#!/bin/sh
# Fixed synthetic files and local evidence commands only; no instrument operations.
set -eu
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 NEW_OUTPUT_DIRECTORY" >&2
    exit 2
fi

run_step() {
    expected=$1
    report=$2
    description=$3
    shift 3
    printf '\n%s\n  Report: %s\n' "$description" "$report" >&2
    # Trace only the public CLI invocation; leave report stdout untouched.
    if (set -x; "$@" > "$report"); then
        code=0
    else
        code=$?
    fi
    printf '  Exit status: %s (expected %s)\n' "$code" "$expected" >&2
    if [ "$code" -ne "$expected" ]; then
        printf '[FAIL] Unexpected exit status; evidence retained in %s\n' "$output" >&2
        [ "$code" -ne 0 ] || code=1
        exit "$code"
    fi
    printf '[ok] Expected exit status\n' >&2
}

fixture=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
# Refuse an existing destination so earlier observations remain unchanged.
if [ -e "$1" ] || [ -L "$1" ]; then
    printf 'Output already exists: %s\nChoose a new directory; the earlier run was left unchanged.\n' "$1" >&2
    exit 1
fi
mkdir "$1"
output=$(CDPATH= cd "$1" && pwd -P)
cp -R "$fixture/bundle" "$output/accepted-run"
cp "$fixture/profile.toml" "$output/profile.toml"
pin=b049d958172b0b013aa9934c66e029d2a33559e13aed9d3e362719e8ce9672f6

# Contract: docs/runbooks/evidence-manifests.md
# CLI -> delegate: packages/mho-lab-cli/src/mho_lab_cli/evidence_cli.py -> evidence_delegate.py
run_step 0 "$output/seal.txt" '[1/5] Seal the synthetic file inventory' \
    mho-lab evidence seal "$output/accepted-run" --output "$output/manifest.toml"
cmp "$fixture/manifest.toml" "$output/manifest.toml"
printf '[ok] Generated seal matches the tracked fixture byte-for-byte\n' >&2

# Contract: docs/runbooks/sealed-offline-review.md
# CLI -> delegate: packages/mho-lab-cli/src/mho_lab_cli/review_cli.py -> review_delegate.py
run_step 0 "$output/accepted.toml" '[2/5] Review the matching inventory, capture and transcripts' \
    mho-lab review inspect --root "$output/accepted-run" \
    --manifest "$output/manifest.toml" --expected-manifest-sha256 "$pin" \
    --profile "$output/profile.toml"

cp -R "$output/accepted-run" "$output/changed-run"
printf '0\n' > "$output/changed-run/queries/01-response.bin"
run_step 1 "$output/changed.toml" '[3/5] Review a changed response against the original seal (expect rejection)' \
    mho-lab review inspect --root "$output/changed-run" \
    --manifest "$output/manifest.toml" --expected-manifest-sha256 "$pin" \
    --profile "$output/profile.toml"
grep -Fx 'stage = "inventory-before"' "$output/changed.toml" > /dev/null
printf '[ok] Rejection stage: inventory-before\n' >&2

# A new seal describes the changed bytes; it cannot make the transcript match TCP.
run_step 0 "$output/mixed-seal.txt" '[4/5] Seal the changed inventory separately' \
    mho-lab evidence seal "$output/changed-run" --output "$output/mixed-manifest.toml"
mixed_pin=$(sed -n 's/^SHA-256: //p' "$output/mixed-seal.txt")
[ "${#mixed_pin}" -eq 64 ]
run_step 1 "$output/mixed.toml" '[5/5] Review the resealed response against the unchanged capture (expect rejection)' \
    mho-lab review inspect --root "$output/changed-run" \
    --manifest "$output/mixed-manifest.toml" --expected-manifest-sha256 "$mixed_pin" \
    --profile "$output/profile.toml"
grep -Fx 'stage = "transcripts"' "$output/mixed.toml" > /dev/null
grep -Fx 'code = "tcp-transcript-mismatch"' "$output/mixed.toml" > /dev/null
printf '[ok] Rejection stage: transcripts; code: tcp-transcript-mismatch\n' >&2
printf '\nSynthetic walkthrough complete: accepted.toml, changed.toml, mixed.toml\n'
