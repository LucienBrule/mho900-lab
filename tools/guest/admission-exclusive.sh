#!/bin/sh
# Private observer controls only: no APK installation or application instrumentation.
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
sample_pid() {
    pid=$(adb shell pidof system_server | tr -d '\r')
    case "$pid" in ''|*[!0-9]*) exit 2;; esac
    printf '%s = %s\n' "$1" "$pid" >> "$run/exclusive-system-server.toml"
}
sample_pid before
system_pid=$pid
adb shell getenforce > "$run/exclusive-enforcing.txt"
adb shell pm path com.rigol.scope > "$run/exclusive-packages.txt" 2>&1 || true
[ ! -s "$run/exclusive-packages.txt" ]
adb shell ps > "$run/exclusive-processes.txt"
adb root > "$run/exclusive-adb-root.txt"
adb wait-for-device
sample_pid after_root
[ "$pid" = "$system_pid" ]
adb shell 'id; cat /proc/self/attr/current' > "$run/exclusive-identity.txt"
cp "$repo/local/guest-tools/exclusive-control/"*.txt "$run/"
cp "$repo/local/guest-tools/exclusive-control/exclusive-control" "$run/exclusive-control.elf"
cp "$repo/experiments/guest-exclusive-control/fixture.toml" "$run/exclusive-fixture.toml"
adb push "$run/exclusive-control.elf" /data/local/tmp/exclusive-control > "$run/exclusive-push.txt"
adb shell chmod 755 /data/local/tmp/exclusive-control
index=0
for mode in cont step step cont; do
    rc=0
    adb shell "/data/local/tmp/exclusive-control $mode" > "$run/exclusive-$index.toml" 2>&1 || rc=$?
    printf 'exit_code = %s\n' "$rc" > "$run/exclusive-$index-status.toml"
    adb pull /data/local/tmp/exclusive-control "$run/exclusive-$index.elf" > "$run/exclusive-$index-pull.txt"
    cmp "$run/exclusive-control.elf" "$run/exclusive-$index.elf"
    sample_pid "after_arm_$index"
    [ "$pid" = "$system_pid" ]
    [ "$rc" = 0 ] || exit 3
    index=$((index+1))
done
adb shell getenforce >> "$run/exclusive-enforcing.txt"
adb shell pm path com.rigol.scope >> "$run/exclusive-packages.txt" 2>&1 || true
adb shell ps >> "$run/exclusive-processes.txt"
[ ! -s "$run/exclusive-packages.txt" ]
