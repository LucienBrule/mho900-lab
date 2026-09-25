#!/bin/sh
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }

# Preserve the already admitted 0..24 regression suite before opening the SPU phase.
"$run/source/admission-transcriptcontrol.sh"

sample_pid() {
    pid=$(adb shell pidof system_server | tr -d '\r')
    case "$pid" in ''|*[!0-9]*) exit 2;; esac
    printf '%s = %s\n' "$1" "$pid" >> "$run/spu-system-server.toml"
}

sample_pid before
system_pid=$pid
adb shell getenforce > "$run/spu-enforcing.txt"
adb shell pm path com.rigol.scope > "$run/spu-packages.txt" 2>&1 || true
[ ! -s "$run/spu-packages.txt" ]
adb shell ps > "$run/spu-processes-before.txt"
! rg -q 'Sparrow|frida' "$run/spu-processes-before.txt"

canonical="$repo/out/spu-transcript/derived-01"
derivation="$repo/experiments/spu-transcript/derivation.toml"
for file in spu-private.bin spu-stock.bin; do
    cp "$canonical/$file" "$run/$file"
done
cp "$derivation" "$run/spu-derivation.toml"
cp "$repo/experiments/spu-transcript/controls.toml" "$run/spu-control-fixture.toml"
for file in spu-private.bin spu-stock.bin; do
    expected=$(yq -p toml -o yaml -r ".files[] | select(.path == \"$file\") | .sha256" "$derivation")
    actual=$(shasum -a 256 "$run/$file"); actual=${actual%% *}
    [ "$actual" = "$expected" ]
done
printf '%s\n' "$derivation" "$canonical/manifest.toml" > "$run/spu-input-sources.txt"
adb push "$run/spu-private.bin" /data/local/tmp/spu-private.bin > "$run/spu-private-push.txt"
adb push "$run/spu-stock.bin" /data/local/tmp/spu-stock.bin > "$run/spu-stock-push.txt"

kotlin "$run/source/PrepareSpuInputControls.main.kts" "$run/spu-private.bin" "$run/spu-invalid" > "$run/spu-invalid-prepare.toml"
invalid_names="magic version profile count reserved binding global derived series-pointer series-config-pointer sample shadow terminal-shadow offset operand truncated trailing"
for name in $invalid_names; do
    file="$run/spu-invalid/$name.bin"
    [ -f "$file" ]
    adb push "$file" "/data/local/tmp/spu-invalid-$name.bin" > "$run/spu-invalid-$name-push.txt"
    rc=0
    adb shell "/data/local/tmp/group-observer control-spu 25 /data/local/tmp/adc-private.bin /data/local/tmp/spu-invalid-$name.bin" \
        > "$run/spu-invalid-$name.toml" 2>&1 || rc=$?
    printf 'exit_code = %s\n' "$rc" > "$run/spu-invalid-$name-status.toml"
    [ "$rc" = 2 ]
    [ "$(rg -c 'spu-input-rejected' "$run/spu-invalid-$name.toml")" = 1 ]
    ! rg -q 'model-mode|group-setup' "$run/spu-invalid-$name.toml"
done
adb pull /data/local/tmp/group-observer "$run/spu-invalid.elf" > "$run/spu-invalid-pull.txt"
cmp "$run/group-control.elf" "$run/spu-invalid.elf"
sample_pid after_invalid
[ "$pid" = "$system_pid" ]

outcome=0
for arm in 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39; do
    rc=0
    adb shell "/data/local/tmp/group-observer control-spu $arm /data/local/tmp/adc-private.bin /data/local/tmp/spu-private.bin" \
        > "$run/spu-$arm.toml" 2>&1 || rc=$?
    printf 'exit_code = %s\n' "$rc" > "$run/spu-$arm-status.toml"
    adb pull /data/local/tmp/group-observer "$run/spu-$arm.elf" > "$run/spu-$arm-pull.txt"
    cmp "$run/group-control.elf" "$run/spu-$arm.elf"
    sample_pid "after_arm_$arm"
    [ "$pid" = "$system_pid" ]
    if [ "$rc" != 78 ]; then outcome=3; break; fi
    kotlin "$run/source/VerifySpuObserver.main.kts" "$run" "$arm" > "$run/spu-$arm-verification.toml" || { outcome=3; break; }
done

adb shell getenforce >> "$run/spu-enforcing.txt"
adb shell pm path com.rigol.scope >> "$run/spu-packages.txt" 2>&1 || true
adb shell ps > "$run/spu-processes-after.txt"
[ "$(tr -d '\r' < "$run/spu-enforcing.txt" | awk 'NF { n++; if ($0 != "Enforcing") bad=1 } END { print n ":" (bad ? 1 : 0) }')" = "2:0" ]
[ ! -s "$run/spu-packages.txt" ]
! rg -q 'Sparrow|frida' "$run/spu-processes-after.txt"
exit "$outcome"
