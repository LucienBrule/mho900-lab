#!/bin/sh
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }

# Complete all existing 0..39 controls and malformed-input checks with this executable.
"$run/source/admission-spucontrol.sh"

sample_pid() {
    pid=$(adb shell pidof system_server | tr -d '\r')
    case "$pid" in ''|*[!0-9]*) exit 2;; esac
    printf '%s = %s\n' "$1" "$pid" >> "$run/remaining-system-server.toml"
}

sample_pid before
system_pid=$pid
adb shell getenforce > "$run/remaining-enforcing.txt"
adb shell pm path com.rigol.scope > "$run/remaining-packages.txt" 2>&1 || true
[ ! -s "$run/remaining-packages.txt" ]
adb shell ps > "$run/remaining-processes-before.txt"
! rg -q 'Sparrow|frida|group-observer' "$run/remaining-processes-before.txt"
cp "$repo/experiments/remaining-init/controls.toml" "$run/remaining-control-fixture.toml"
cp "$repo/experiments/remaining-init/grammar.toml" "$run/remaining-grammar.toml"

outcome=0
for arm in 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58; do
    rc=0
    adb shell "/data/local/tmp/group-observer control-remaining $arm /data/local/tmp/adc-private.bin /data/local/tmp/spu-private.bin" \
        > "$run/remaining-$arm.toml" 2>&1 || rc=$?
    printf 'exit_code = %s\n' "$rc" > "$run/remaining-$arm-status.toml"
    adb pull /data/local/tmp/group-observer "$run/remaining-$arm.elf" > "$run/remaining-$arm-pull.txt"
    cmp "$run/group-control.elf" "$run/remaining-$arm.elf"
    sample_pid "after_arm_$arm"
    [ "$pid" = "$system_pid" ]
    if [ "$rc" != 78 ]; then outcome=3; break; fi
    kotlin "$run/source/VerifyRemainingObserver.main.kts" "$run" "$arm" \
        > "$run/remaining-$arm-verification.toml" 2> "$run/remaining-$arm-verification.stderr" || { outcome=3; break; }
done

adb shell getenforce >> "$run/remaining-enforcing.txt"
adb shell pm path com.rigol.scope >> "$run/remaining-packages.txt" 2>&1 || true
adb shell ps > "$run/remaining-processes-after.txt"
[ "$(tr -d '\r' < "$run/remaining-enforcing.txt" | awk 'NF { n++; if ($0 != "Enforcing") bad=1 } END { print n ":" (bad ? 1 : 0) }')" = "2:0" ]
[ ! -s "$run/remaining-packages.txt" ]
! rg -q 'Sparrow|frida|group-observer' "$run/remaining-processes-after.txt"
exit "$outcome"
