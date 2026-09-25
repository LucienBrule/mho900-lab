#!/bin/sh
# Private observer controls only: no APK installation or application instrumentation.
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
profile=${EXECUTION_PROFILE:-strict}
case "$profile" in strict) suffix=;; cached-enable) suffix=-profile;; *) exit 2;; esac
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
sample_pid() {
    pid=$(adb shell pidof system_server | tr -d '\r')
    case "$pid" in ''|*[!0-9]*) exit 2;; esac
    printf '%s = %s\n' "$1" "$pid" >> "$run/execution-system-server.toml"
}
sample_pid before
system_pid=$pid
adb shell getenforce > "$run/execution-enforcing.txt"
adb shell pm path com.rigol.scope > "$run/execution-packages.txt" 2>&1 || true
[ ! -s "$run/execution-packages.txt" ]
adb shell ps > "$run/execution-processes.txt"
adb root > "$run/execution-adb-root.txt"
adb wait-for-device
sample_pid after_root
[ "$pid" = "$system_pid" ]
adb shell 'id; cat /proc/self/attr/current' > "$run/execution-identity.txt"
cp "$repo/local/guest-tools/execution-stop$suffix/"*.txt "$run/"
cp "$repo/local/guest-tools/execution-stop$suffix/execution-stop" "$run/execution-control.elf"
cp "$repo/experiments/guest-execution-stop/fixture.toml" "$run/execution-fixture.toml"
if [ "$profile" = cached-enable ]; then
    cp "$repo/experiments/guest-execution-stop/profile.toml" "$run/execution-profile.toml"
fi
adb push "$run/execution-control.elf" /data/local/tmp/execution-control > "$run/execution-push.txt"
adb shell chmod 755 /data/local/tmp/execution-control
index=0
outcome=0
for mode in cont break miss break cont; do
    rc=0
    adb shell "/data/local/tmp/execution-control $mode" > "$run/execution-$index.toml" 2>&1 || rc=$?
    printf 'exit_code = %s\n' "$rc" > "$run/execution-$index-status.toml"
    adb pull /data/local/tmp/execution-control "$run/execution-$index.elf" > "$run/execution-$index-pull.txt"
    cmp "$run/execution-control.elf" "$run/execution-$index.elf"
    sample_pid "after_arm_$index"
    [ "$pid" = "$system_pid" ]
    if [ "$rc" != 0 ]; then outcome=3; break; fi
    index=$((index+1))
done
adb shell getenforce >> "$run/execution-enforcing.txt"
adb shell pm path com.rigol.scope >> "$run/execution-packages.txt" 2>&1 || true
adb shell ps >> "$run/execution-processes.txt"
[ ! -s "$run/execution-packages.txt" ]
exit "$outcome"
