#!/bin/sh
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
sample_pid() {
    pid=$(adb shell pidof system_server | tr -d '\r')
    case "$pid" in ''|*[!0-9]*) exit 2;; esac
    printf '%s = %s\n' "$1" "$pid" >> "$run/coverage-system-server.toml"
}
sample_pid before
system_pid=$pid
adb shell getenforce > "$run/coverage-enforcing.txt"
adb shell pm path com.rigol.scope > "$run/coverage-packages.txt" 2>&1 || true
[ ! -s "$run/coverage-packages.txt" ]
adb root > "$run/coverage-adb-root.txt"
adb wait-for-device
sample_pid after_root
[ "$pid" = "$system_pid" ]
cp "$repo/local/guest-tools/thread-coverage/"*.txt "$run/"
cp "$repo/local/guest-tools/thread-coverage/thread-coverage" "$run/coverage-control.elf"
cp "$repo/experiments/guest-thread-discovery/fixture.toml" "$run/coverage-fixture.toml"
adb push "$run/coverage-control.elf" /data/local/tmp/thread-coverage > "$run/coverage-push.txt"
adb shell chmod 755 /data/local/tmp/thread-coverage
outcome=0
for arm in 0 1; do
    rc=0
    adb shell "/data/local/tmp/thread-coverage control $arm" > "$run/coverage-$arm.toml" 2>&1 || rc=$?
    printf 'exit_code = %s\n' "$rc" > "$run/coverage-$arm-status.toml"
    adb pull /data/local/tmp/thread-coverage "$run/coverage-$arm.elf" > "$run/coverage-$arm-pull.txt"
    cmp "$run/coverage-control.elf" "$run/coverage-$arm.elf"
    sample_pid "after_arm_$arm"
    [ "$pid" = "$system_pid" ]
    if [ "$rc" != 0 ]; then outcome=3; break; fi
    kotlin "$run/source/VerifyCoverage.main.kts" "$run" "$arm" > "$run/coverage-$arm-verification.toml" || { outcome=3; break; }
done
adb shell getenforce >> "$run/coverage-enforcing.txt"
adb shell pm path com.rigol.scope >> "$run/coverage-packages.txt" 2>&1 || true
adb shell ps > "$run/coverage-processes-after.txt"
[ ! -s "$run/coverage-packages.txt" ]
exit "$outcome"
