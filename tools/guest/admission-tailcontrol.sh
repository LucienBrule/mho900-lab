#!/bin/sh
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }

# Preserve all prior 0..58 controls and malformed-input checks with this executable.
"$run/source/admission-remainingcontrol.sh"

sample_pid() {
    pid=$(adb shell pidof system_server | tr -d '\r')
    case "$pid" in ''|*[!0-9]*) exit 2;; esac
    printf '%s = %s\n' "$1" "$pid" >> "$run/tail-system-server.toml"
}
sample_pid before
system_pid=$pid
adb shell getenforce > "$run/tail-enforcing.txt"
adb shell pm path com.rigol.scope > "$run/tail-packages.txt" 2>&1 || true
[ ! -s "$run/tail-packages.txt" ]
adb shell ps > "$run/tail-processes-before.txt"
! rg -q 'Sparrow|frida|group-observer' "$run/tail-processes-before.txt"
cp "$repo/experiments/init-tail/candidate.toml" "$run/tail-candidate.toml"
cp "$repo/experiments/init-tail/controls-handoff.toml" "$run/tail-control-fixture.toml"
cp "$repo/experiments/init-tail/handoff-profile.toml" "$run/tail-handoff-profile.toml"
cp "$repo/experiments/init-tail/grammar.toml" "$run/tail-grammar.toml"

arms=$(yq -p toml -o yaml -r '.arms[].id' "$run/tail-control-fixture.toml")
[ -n "$arms" ]
outcome=0
for arm in $arms; do
    case "$arm" in ''|*[!0-9]*) exit 2;; esac
    rc=0
    adb shell "/data/local/tmp/group-observer control-tail $arm /data/local/tmp/adc-private.bin /data/local/tmp/spu-private.bin" \
        > "$run/tail-$arm.toml" 2>&1 || rc=$?
    printf 'exit_code = %s\n' "$rc" > "$run/tail-$arm-status.toml"
    adb pull /data/local/tmp/group-observer "$run/tail-$arm.elf" > "$run/tail-$arm-pull.txt"
    cmp "$run/group-control.elf" "$run/tail-$arm.elf"
    sample_pid "after_arm_$arm"
    [ "$pid" = "$system_pid" ]
    if [ "$rc" != 78 ]; then outcome=3; break; fi
    kotlin "$run/source/VerifyInitTailObserver.main.kts" "$run" "$arm" \
        > "$run/tail-$arm-verification.toml" 2> "$run/tail-$arm-verification.stderr" || { outcome=3; break; }
done

adb shell getenforce >> "$run/tail-enforcing.txt"
adb shell pm path com.rigol.scope >> "$run/tail-packages.txt" 2>&1 || true
adb shell ps > "$run/tail-processes-after.txt"
[ "$(tr -d '\r' < "$run/tail-enforcing.txt" | awk 'NF { n++; if ($0 != "Enforcing") bad=1 } END { print n ":" (bad ? 1 : 0) }')" = "2:0" ]
[ ! -s "$run/tail-packages.txt" ]
! rg -q 'Sparrow|frida|group-observer' "$run/tail-processes-after.txt"
exit "$outcome"
