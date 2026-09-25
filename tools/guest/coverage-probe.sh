#!/bin/sh
# Stock coverage-only snapshot; the mapped device is never supplied.
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
final_sample() {
    rc=$?
    trap - EXIT
    adb shell getenforce > "$run/native-final-enforcing.txt" 2>&1 || true
    adb shell pidof system_server > "$run/native-final-system-server.txt" 2>&1 || true
    exit "$rc"
}
trap final_sample EXIT
cp "$repo/local/guest-tools/thread-coverage/"*.txt "$run/"
cp "$repo/local/guest-tools/thread-coverage/thread-coverage" "$run/coverage-control.elf"
cp "$repo/experiments/guest-thread-discovery/fixture.toml" "$run/coverage-fixture.toml"
adb push "$run/coverage-control.elf" /data/local/tmp/thread-coverage > "$run/coverage-push.txt"
adb shell chmod 755 /data/local/tmp/thread-coverage
pid=$(adb shell pidof com.rigol.scope | tr -d '\r')
case "$pid" in ''|*[!0-9]*) exit 2;; esac
printf 'pid = %s\n' "$pid" > "$run/native-app-pid.toml"
snapshot_rc=0
adb shell "cat /proc/$pid/cmdline; cat /proc/$pid/attr/current; cat /proc/$pid/maps" \
    > "$run/native-snapshot-composite.txt" 2> "$run/native-snapshot-composite-error.txt" || snapshot_rc=$?
printf 'exit_code = %s\n' "$snapshot_rc" > "$run/native-snapshot-composite-status.toml"
for part in cmdline label maps; do
    node=$part
    [ "$part" != label ] || node=attr/current
    snapshot_rc=0
    adb shell "cat /proc/$pid/$node" > "$run/native-snapshot-$part.txt" \
        2> "$run/native-snapshot-$part-error.txt" || snapshot_rc=$?
    printf 'exit_code = %s\n' "$snapshot_rc" > "$run/native-snapshot-$part-status.toml"
done
kotlin "$run/source/VerifySnapshot.main.kts" "$run" > "$run/native-snapshot-verification.toml"
cat "$run/native-snapshot-cmdline.txt" "$run/native-snapshot-label.txt" > "$run/native-before.txt"
printf '\n' >> "$run/native-before.txt"
cat "$run/native-snapshot-maps.txt" >> "$run/native-before.txt"
actual=$(unzip -p "$run/installed.apk" lib/arm64-v8a/libscope-auklet.so | shasum -a 256); actual=${actual%% *}
[ "$actual" = 4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e ]
adb shell 'test ! -e /dev/xdma0_bypass && echo device_absent = true' > "$run/coverage-device-before.toml"
rc=0
adb shell "/data/local/tmp/thread-coverage stock $pid" > "$run/native-events.toml" 2>&1 || rc=$?
printf 'exit_code = %s\n' "$rc" > "$run/native-status.toml"
adb pull /data/local/tmp/thread-coverage "$run/coverage-executed.elf" > "$run/coverage-executed-pull.txt"
cmp "$run/coverage-control.elf" "$run/coverage-executed.elf"
adb shell 'test ! -e /dev/xdma0_bypass && echo device_absent = true' > "$run/coverage-device-after.toml"
adb shell getenforce > "$run/native-enforcing.txt"
sleep 2
exit "$rc"
