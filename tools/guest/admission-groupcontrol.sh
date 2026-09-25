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
cp "$repo/local/guest-tools/group-observer/"*.txt "$run/"
cp "$repo/local/guest-tools/group-observer/group-observer" "$run/group-control.elf"
cp "$repo/experiments/group-observer/fixture.toml" "$run/group-fixture.toml"
adb push "$run/group-control.elf" /data/local/tmp/group-observer > "$run/group-push.txt"
adb shell chmod 755 /data/local/tmp/group-observer
arms="0 1 2"
if [ "${ADMISSION_MODE:-groupcontrol}" = nextcontrol ] || [ "${ADMISSION_MODE:-groupcontrol}" = writecontrol ] || [ "${ADMISSION_MODE:-groupcontrol}" = paircontrol ]; then
    arms="0 1 2 3 4"
    cp "$repo/experiments/group-observer/continuation.toml" "$run/continuation-fixture.toml"
fi
if [ "${ADMISSION_MODE:-groupcontrol}" = writecontrol ] || [ "${ADMISSION_MODE:-groupcontrol}" = paircontrol ]; then
    arms="0 1 2 3 4 5 6 7 8"
    cp "$repo/experiments/group-observer/one-write.toml" "$run/write-fixture.toml"
fi
if [ "${ADMISSION_MODE:-groupcontrol}" = paircontrol ]; then
    arms="0 1 2 3 4 5 6 7 8 9 10 11 12"
    cp "$repo/experiments/group-observer/two-writes.toml" "$run/pair-write-fixture.toml"
fi
outcome=0
for arm in $arms; do
    rc=0
    adb shell "/data/local/tmp/group-observer control $arm" > "$run/group-$arm.toml" 2>&1 || rc=$?
    printf 'exit_code = %s\n' "$rc" > "$run/group-$arm-status.toml"
    adb pull /data/local/tmp/group-observer "$run/group-$arm.elf" > "$run/group-$arm-pull.txt"
    cmp "$run/group-control.elf" "$run/group-$arm.elf"
    sample_pid "after_arm_$arm"
    [ "$pid" = "$system_pid" ]
    expected=78; [ "$arm" != 0 ] || expected=0
    if [ "$rc" != "$expected" ]; then outcome=3; break; fi
    kotlin "$run/source/VerifyGroupObserver.main.kts" "$run" "$arm" > "$run/group-$arm-verification.toml" || { outcome=3; break; }
done
adb shell getenforce >> "$run/group-enforcing.txt"
adb shell pm path com.rigol.scope >> "$run/group-packages.txt" 2>&1 || true
adb shell ps > "$run/group-processes-after.txt"
[ ! -s "$run/group-packages.txt" ]
exit "$outcome"
