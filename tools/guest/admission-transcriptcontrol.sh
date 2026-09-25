#!/bin/sh
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }

sample_pid() {
    pid=$(adb shell pidof system_server | tr -d '\r')
    case "$pid" in ''|*[!0-9]*) exit 2;; esac
    printf '%s = %s\n' "$1" "$pid" >> "$run/group-system-server.toml"
}

sample_pid before
system_pid=$pid
adb shell getenforce > "$run/group-enforcing.txt"
adb shell pm path com.rigol.scope > "$run/group-packages.txt" 2>&1 || true
[ ! -s "$run/group-packages.txt" ]
adb root > "$run/group-adb-root.txt"
adb wait-for-device
sample_pid after_root
[ "$pid" = "$system_pid" ]

cp "$repo/experiments/group-observer/fixture.toml" "$run/group-fixture.toml"
cp "$repo/experiments/group-observer/continuation.toml" "$run/continuation-fixture.toml"
cp "$repo/experiments/group-observer/one-write.toml" "$run/write-fixture.toml"
cp "$repo/experiments/group-observer/two-writes.toml" "$run/pair-write-fixture.toml"
cp "$repo/experiments/adc-transcript/controls.toml" "$run/transcript-fixture.toml"
cp "$repo/local/guest-tools/group-observer/"*.txt "$run/"
cp "$repo/local/guest-tools/group-observer/group-observer" "$run/group-control.elf"
adb push "$run/group-control.elf" /data/local/tmp/group-observer > "$run/group-push.txt"
adb shell chmod 755 /data/local/tmp/group-observer

canonical="$repo/out/adc-transcript/derived-01"
derivation="$repo/experiments/adc-transcript/derivation.toml"
for file in adc-private.bin adc-private-one.bin adc-stock.bin adc-transcript.tsv; do
    cp "$canonical/$file" "$run/$file"
done
cp "$repo/experiments/adc-transcript/reference.tsv" "$run/reference.tsv"
cp "$derivation" "$run/derivation.toml"
expected=$(yq -p toml -o yaml -r '.files[] | select(.path == "adc-private.bin") | .sha256' "$derivation")
actual=$(shasum -a 256 "$run/adc-private.bin"); actual=${actual%% *}; [ "$actual" = "$expected" ]
expected=$(yq -p toml -o yaml -r '.files[] | select(.path == "adc-private-one.bin") | .sha256' "$derivation")
actual=$(shasum -a 256 "$run/adc-private-one.bin"); actual=${actual%% *}; [ "$actual" = "$expected" ]
expected=$(yq -p toml -o yaml -r '.files[] | select(.path == "adc-stock.bin") | .sha256' "$derivation")
actual=$(shasum -a 256 "$run/adc-stock.bin"); actual=${actual%% *}; [ "$actual" = "$expected" ]
expected=$(yq -p toml -o yaml -r '.files[] | select(.path == "adc-transcript.tsv") | .sha256' "$derivation")
actual=$(shasum -a 256 "$run/adc-transcript.tsv"); actual=${actual%% *}; [ "$actual" = "$expected" ]
expected=$(yq -p toml -o yaml -r '.independent_transcript_sha256' "$derivation")
actual=$(shasum -a 256 "$run/reference.tsv"); actual=${actual%% *}; [ "$actual" = "$expected" ]
printf '%s\n' "$derivation" "$canonical/manifest.toml" > "$run/transcript-input-sources.txt"

adb push "$run/adc-private.bin" /data/local/tmp/adc-private.bin > "$run/adc-private-push.txt"
adb push "$run/adc-private-one.bin" /data/local/tmp/adc-private-one.bin > "$run/adc-private-one-push.txt"
kotlin "$run/source/PrepareAdcInputControls.main.kts" "$run/adc-private.bin" "$run/adc-invalid" > "$run/adc-invalid-prepare.toml"
invalid_names="magic version profile count reference-count reserved truncated trailing oversized binding table-count width offset"
for name in $invalid_names; do
    file="$run/adc-invalid/$name.bin"
    [ -f "$file" ]
    adb push "$file" "/data/local/tmp/adc-invalid-$name.bin" > "$run/adc-invalid-$name-push.txt"
    rc=0
    adb shell "/data/local/tmp/group-observer control-transcript 13 /data/local/tmp/adc-invalid-$name.bin" \
        > "$run/adc-invalid-$name.toml" 2>&1 || rc=$?
    printf 'exit_code = %s\n' "$rc" > "$run/adc-invalid-$name-status.toml"
    [ "$rc" = 2 ]
    rg -q 'transcript-input-rejected' "$run/adc-invalid-$name.toml"
    ! rg -q 'model-mode|group-setup' "$run/adc-invalid-$name.toml"
done
adb pull /data/local/tmp/group-observer "$run/group-invalid.elf" > "$run/group-invalid-pull.txt"
cmp "$run/group-control.elf" "$run/group-invalid.elf"
sample_pid after_invalid
[ "$pid" = "$system_pid" ]

outcome=0
for arm in 0 1 2 3 4 5 6 7 8 9 10 11 12; do
    rc=0
    adb shell "/data/local/tmp/group-observer control $arm" > "$run/group-$arm.toml" 2>&1 || rc=$?
    printf 'exit_code = %s\n' "$rc" > "$run/group-$arm-status.toml"
    adb pull /data/local/tmp/group-observer "$run/group-$arm.elf" > "$run/group-$arm-pull.txt"
    cmp "$run/group-control.elf" "$run/group-$arm.elf"
    sample_pid "after_arm_$arm"
    [ "$pid" = "$system_pid" ]
    expected=78; [ "$arm" = 0 ] && expected=0
    if [ "$rc" != "$expected" ]; then outcome=3; break; fi
    kotlin "$run/source/VerifyGroupObserver.main.kts" "$run" "$arm" > "$run/group-$arm-verification.toml" || { outcome=3; break; }
done

if [ "$outcome" = 0 ]; then
    for arm in 13 14 15 16 17 18 19 20 21 22 23 24; do
        input=/data/local/tmp/adc-private.bin
        [ "$arm" = 18 ] && input=/data/local/tmp/adc-private-one.bin
        rc=0
        adb shell "/data/local/tmp/group-observer control-transcript $arm $input" > "$run/group-$arm.toml" 2>&1 || rc=$?
        printf 'exit_code = %s\n' "$rc" > "$run/group-$arm-status.toml"
        adb pull /data/local/tmp/group-observer "$run/group-$arm.elf" > "$run/group-$arm-pull.txt"
        cmp "$run/group-control.elf" "$run/group-$arm.elf"
        sample_pid "after_arm_$arm"
        [ "$pid" = "$system_pid" ]
        if [ "$rc" != 78 ]; then outcome=3; break; fi
        kotlin "$run/source/VerifyAdcObserver.main.kts" "$run" "$arm" > "$run/group-$arm-verification.toml" || { outcome=3; break; }
    done
fi

adb shell getenforce >> "$run/group-enforcing.txt"
adb shell pm path com.rigol.scope >> "$run/group-packages.txt" 2>&1 || true
adb shell ps > "$run/group-processes-after.txt"
[ "$(tr -d '\r' < "$run/group-enforcing.txt" | awk 'NF { n++; if ($0 != "Enforcing") bad=1 } END { print n ":" (bad ? 1 : 0) }')" = "2:0" ]
[ ! -s "$run/group-packages.txt" ]
exit "$outcome"
