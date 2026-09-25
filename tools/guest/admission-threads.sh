#!/bin/sh
# Private thread-observer controls; no application installation or admission fixture.
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
sample_pid() {
    pid=$(adb shell pidof system_server | tr -d '\r')
    case "$pid" in ''|*[!0-9]*) exit 2;; esac
    printf '%s = %s\n' "$1" "$pid" >> "$run/thread-system-server.toml"
}
sample_pid before
system_pid=$pid
adb shell getenforce > "$run/thread-enforcing.txt"
adb shell pm path com.rigol.scope > "$run/thread-packages.txt" 2>&1 || true
[ ! -s "$run/thread-packages.txt" ]
adb root > "$run/thread-adb-root.txt"
adb wait-for-device
sample_pid after_root
[ "$pid" = "$system_pid" ]
adb shell 'id; cat /proc/self/attr/current' > "$run/thread-identity.txt"
cp "$repo/local/guest-tools/thread-control/"*.txt "$run/"
cp "$repo/local/guest-tools/thread-control/thread-control" "$run/thread-control.elf"
cp "$repo/experiments/guest-thread-control/fixture.toml" "$run/thread-fixture.toml"
adb push "$run/thread-control.elf" /data/local/tmp/thread-control > "$run/thread-push.txt"
adb shell chmod 755 /data/local/tmp/thread-control
outcome=0
for arm in 0 1 2; do
    rc=0
    adb shell "/data/local/tmp/thread-control $arm" > "$run/thread-$arm.toml" 2>&1 || rc=$?
    printf 'exit_code = %s\n' "$rc" > "$run/thread-$arm-status.toml"
    adb pull /data/local/tmp/thread-control "$run/thread-$arm.elf" > "$run/thread-$arm-pull.txt"
    cmp "$run/thread-control.elf" "$run/thread-$arm.elf"
    sample_pid "after_arm_$arm"
    [ "$pid" = "$system_pid" ]
    if [ "$rc" != 0 ]; then outcome=3; break; fi
    kotlin "$run/source/VerifyThreads.main.kts" "$run" "$arm" > "$run/thread-$arm-verification.toml" || { outcome=3; break; }
done
adb shell getenforce >> "$run/thread-enforcing.txt"
adb shell pm path com.rigol.scope >> "$run/thread-packages.txt" 2>&1 || true
adb shell ps > "$run/thread-processes-after.txt"
[ ! -s "$run/thread-packages.txt" ]
exit "$outcome"
