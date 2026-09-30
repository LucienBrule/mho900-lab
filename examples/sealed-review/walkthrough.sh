#!/bin/sh
# Fixed synthetic files and local evidence commands only; no instrument operations.
set -eu
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 NEW_OUTPUT_DIRECTORY" >&2
    exit 2
fi
fixture=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
# Refuse an existing destination so earlier observations remain unchanged.
mkdir "$1"
output=$(CDPATH= cd "$1" && pwd -P)
cp -R "$fixture/bundle" "$output/accepted-run"
cp "$fixture/profile.toml" "$output/profile.toml"
pin=b049d958172b0b013aa9934c66e029d2a33559e13aed9d3e362719e8ce9672f6
mho-lab evidence seal "$output/accepted-run" --output "$output/manifest.toml" > "$output/seal.txt"
cmp "$fixture/manifest.toml" "$output/manifest.toml"
mho-lab review inspect --root "$output/accepted-run" \
    --manifest "$output/manifest.toml" --expected-manifest-sha256 "$pin" \
    --profile "$output/profile.toml" > "$output/accepted.toml"

cp -R "$output/accepted-run" "$output/changed-run"
printf '0\n' > "$output/changed-run/queries/01-response.bin"
if mho-lab review inspect --root "$output/changed-run" \
    --manifest "$output/manifest.toml" --expected-manifest-sha256 "$pin" \
    --profile "$output/profile.toml" > "$output/changed.toml"; then
    echo "Expected the changed inventory to reject." >&2
    exit 1
else
    code=$?
    [ "$code" -eq 1 ] || exit "$code"
fi

grep -Fx 'stage = "inventory-before"' "$output/changed.toml" > /dev/null

# A new seal describes the changed bytes; it cannot make the transcript match TCP.
mho-lab evidence seal "$output/changed-run" --output "$output/mixed-manifest.toml" > "$output/mixed-seal.txt"
mixed_pin=$(sed -n 's/^SHA-256: //p' "$output/mixed-seal.txt")
[ "${#mixed_pin}" -eq 64 ]
if mho-lab review inspect --root "$output/changed-run" \
    --manifest "$output/mixed-manifest.toml" --expected-manifest-sha256 "$mixed_pin" \
    --profile "$output/profile.toml" > "$output/mixed.toml"; then
    echo "Expected the resealed transcript disagreement to reject." >&2
    exit 1
else
    code=$?
    [ "$code" -eq 1 ] || exit "$code"
fi
grep -Fx 'stage = "transcripts"' "$output/mixed.toml" > /dev/null
grep -Fx 'code = "tcp-transcript-mismatch"' "$output/mixed.toml" > /dev/null
printf 'Synthetic walkthrough complete: accepted.toml, changed.toml, mixed.toml\n'
