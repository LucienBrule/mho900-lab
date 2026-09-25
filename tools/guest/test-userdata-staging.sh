#!/bin/sh
set -eu
root=${1:?Usage: test-userdata-staging.sh NEW_OUTPUT_DIRECTORY}
[ ! -e "$root" ]
mkdir -p "$root"
stager=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/stage-userdata.sh
printf 'immutable userdata fixture\n' > "$root/source.img"
sh "$stager" "$root/source.img" "$root/copy.img" "$root/receipt.toml" 0
printf 'changed copy only\n' > "$root/copy.img"
printf 'immutable userdata fixture\n' | cmp - "$root/source.img"
rejected() {
    key=$1; shift
    rc=0
    sh "$stager" "$@" > "$root/$key.stdout" 2> "$root/$key.stderr" || rc=$?
    printf 'status = %s\n' "$rc" > "$root/$key.toml"
    [ "$rc" -ne 0 ]
}
rejected occupied "$root/source.img" "$root/copy.img" "$root/occupied-receipt.toml" 0
# These fixtures contain links only to test rejection before any copy or write.
ln -s source.img "$root/linked-source.img"
rejected linked-source "$root/linked-source.img" "$root/link-copy.img" "$root/link-receipt.toml" 0
ln -s missing.img "$root/linked-target.img"
rejected linked-target "$root/source.img" "$root/linked-target.img" "$root/target-link-receipt.toml" 0
rejected low-space "$root/source.img" "$root/no-space.img" "$root/no-space-receipt.toml" 999999999999
[ ! -e "$root/link-copy.img" ] && [ ! -e "$root/missing.img" ] && [ ! -e "$root/no-space.img" ]
printf 'immutable userdata fixture\n' | cmp - "$root/source.img"
cat > "$root/summary.toml" <<'RESULT'
schema_version = "mho900-lab.userdata-staging-controls/1"
result = "accepted"
positive_cases = 1
source_unchanged_after_copy_mutation = true
negative_cases = 4
negative_cases_rejected = 4
new_guest_runs = 0
RESULT
