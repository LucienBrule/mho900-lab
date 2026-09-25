#!/bin/sh
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
controls="$repo/local/guest-inputs/admission-controls"
apk="$repo/local/guest-inputs/Sparrow.apk"
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
install_control() {
    name=$1
    rc=0
    adb install "$controls/$name.apk" > "$run/control-$name.txt" 2>&1 || rc=$?
    [ "$rc" != 0 ] && grep -q INSTALL_FAILED_SHARED_USER_INCOMPATIBLE "$run/control-$name.txt"
}
# Re-establish the unmodified admission decision before starting instrumentation.
rc=0
adb install "$apk" > "$run/unhooked-stock.txt" 2>&1 || rc=$?
if [ "$rc" = 0 ] || ! grep -q INSTALL_FAILED_SHARED_USER_INCOMPATIBLE "$run/unhooked-stock.txt"; then
    echo 'Unhooked baseline did not reproduce' >&2; exit 2
fi
"$run/source/admission-inspect.sh"
adb shell 'oatdump --oat-file=/system/framework/oat/arm64/services.odex --class-filter=PackageManagerService --method-filter=scanPackageDirtyLI' \
    > "$run/scan-package-oatdump.txt" 2>&1
for name in unrelated different-signer changed-bytes; do
    "$sdk/build-tools/35.0.0/apksigner" verify --verbose --print-certs "$controls/$name.apk" \
        > "$run/control-$name-signature.txt"
    shasum -a 256 "$controls/$name.apk" >> "$run/control-inputs.txt"
done
grep -q 'f48e7189aac174df7fd19acf58b6d15832760fcf25ac0a6d4bcd5fc1974d4c03' \
    "$run/control-changed-bytes-signature.txt"
frida_pid=
app_log_pid=
detach() {
    if [ -n "$frida_pid" ]; then
        kill "$frida_pid" 2>/dev/null || true
        wait "$frida_pid" 2>/dev/null || true
        frida_pid=
    fi
}
cleanup() {
    detach
    if [ -n "$app_log_pid" ]; then
        kill "$app_log_pid" 2>/dev/null || true
        wait "$app_log_pid" 2>/dev/null || true
    fi
}
trap cleanup EXIT
trap 'exit 130' INT TERM
system_pid=$(adb shell pidof system_server | tr -d '\r')
gtimeout -k 2 180 "$repo/local/guest-tools/frida-16.7.19/venv/bin/frida" -H 127.0.0.1:27043 \
    -p "$system_pid" -l "$run/source/labeling-exception.js" -q -t 45 --exit-on-error --no-auto-reload \
    > "$run/admission-hook.txt" 2>&1 &
frida_pid=$!
deadline=$(( $(date +%s) + 25 ))
until grep -q '^admission-exception-ready' "$run/admission-hook.txt"; do
    kill -0 "$frida_pid"
    [ "$(date +%s)" -lt "$deadline" ] || exit 1
    sleep 1
done
install_control unrelated
grep -q '^REJECT lab.mho900.admission.control reason=package' "$run/admission-hook.txt"
install_control different-signer
grep -q '^REJECT com.rigol.scope reason=signer' "$run/admission-hook.txt"
install_control changed-bytes
grep -q '^REJECT com.rigol.scope reason=digest' "$run/admission-hook.txt"
if grep -Eq 'ADMIT|LABEL|GUARD-ERROR' "$run/admission-hook.txt"; then
    echo 'Unexpected control admission or guard error' >&2; exit 2
fi
rc=0
adb install "$apk" > "$run/install.txt" 2>&1 || rc=$?
if [ "$rc" != 0 ] || ! grep -q '^Success' "$run/install.txt"; then
    printf 'install = "failed"\nlaunch = "not_reached"\n' > "$run/probe-result.toml"
    exit 0
fi
grep -q '^ADMIT exact-stock shared-user-error=-8' "$run/admission-hook.txt"
grep -q '^LABEL exact-stock uid=1000 before=default after=platform' "$run/admission-hook.txt"
printf 'install = "admitted"\nlaunch = "not_reached"\n' > "$run/probe-result.toml"
# Let the CLI unload and detach normally. SIGTERM cancels its cleanup I/O.
detach_rc=0
wait "$frida_pid" || detach_rc=$?
frida_pid=
printf 'exit_code = %s\n' "$detach_rc" > "$run/frida-detach-status.toml"
[ "$detach_rc" = 0 ]
adb shell 'kill $(pidof admission-frida)' > "$run/frida-stop.txt" 2>&1
after_pid=$(adb shell pidof system_server | tr -d '\r')
printf 'before = %s\nafter = %s\n' "$system_pid" "$after_pid" > "$run/system-server-pid.toml"
[ "$after_pid" = "$system_pid" ]
adb shell 'cat /proc/$(pidof zygote64)/maps' > "$run/zygote-maps.txt"
if grep -qi frida "$run/zygote-maps.txt"; then
    echo 'Unexpected Frida mapping in zygote' >&2; exit 2
fi
# A fresh call after detachment must again use original shared-UID verification.
rc=0
adb install -r "$apk" > "$run/detached-stock-update.txt" 2>&1 || rc=$?
if [ "$rc" = 0 ] || ! grep -q INSTALL_FAILED_SHARED_USER_INCOMPATIBLE "$run/detached-stock-update.txt"; then
    echo 'Original verification was not restored' >&2; exit 2
fi
adb shell dumpsys package com.rigol.scope > "$run/package-state.txt"
adb pull /data/system/packages.xml "$run/packages.xml" > "$run/packages-pull.txt" 2>&1
installed=$(adb shell pm path com.rigol.scope | tr -d '\r' | sed -n 's/^package://p')
[ -n "$installed" ]
adb pull "$installed" "$run/installed.apk" > "$run/installed-pull.txt" 2>&1
actual=$(shasum -a 256 "$run/installed.apk"); actual=${actual%% *}
[ "$actual" = 6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b ]
"$sdk/build-tools/35.0.0/apksigner" verify --print-certs "$run/installed.apk" \
    > "$run/installed-signature.txt"
# adb root restarts adbd, so use a new collector for the application phase.
gtimeout -k 2 180 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 logcat -b all -v threadtime \
    > "$run/application-logcat.txt" 2>&1 &
app_log_pid=$!
launch_rc=0
printf 'install = "admitted"\nlaunch = "attempted"\n' > "$run/probe-result.toml"
# Observe labels without attaching to or changing the application process.
adb shell 'i=0; while [ "$i" -lt 25 ]; do ps -Z; sleep 1; i=$((i+1)); done' \
    > "$run/process-labels.txt" 2>&1 &
label_pid=$!
adb shell am start -W -n com.rigol.scope/.SplashActivity > "$run/launch.txt" 2>&1 || launch_rc=$?
printf 'exit_code = %s\n' "$launch_rc" > "$run/launch-status.toml"
sleep 15
wait "$label_pid" || true
if [ "${ADMISSION_MODE:-label}" = startup ]; then
    "$run/source/startup-trace.sh"
fi
if [ "${ADMISSION_MODE:-label}" = mapping ]; then
    mapping_rc=0
    "$run/source/mapping-probe.sh" || mapping_rc=$?
    printf 'exit_code = %s\n' "$mapping_rc" > "$run/mapping-helper-status.toml"
fi
if [ "${ADMISSION_MODE:-label}" = syscall ]; then
    syscall_rc=0
    "$run/source/syscall-probe.sh" || syscall_rc=$?
    printf 'exit_code = %s\n' "$syscall_rc" > "$run/syscall-helper-status.toml"
fi
if [ "${ADMISSION_MODE:-label}" = native ]; then
    native_rc=0
    "$run/source/native-probe.sh" || native_rc=$?
    printf 'exit_code = %s\n' "$native_rc" > "$run/native-helper-status.toml"
fi
if [ "${ADMISSION_MODE:-label}" = coverage ]; then
    native_rc=0
    "$run/source/coverage-probe.sh" || native_rc=$?
    printf 'exit_code = %s\n' "$native_rc" > "$run/native-helper-status.toml"
fi
adb shell pidof com.rigol.scope > "$run/app-pid.txt" 2>&1 || true
adb shell ps > "$run/processes.txt" 2>&1
adb shell dumpsys activity activities > "$run/activities.txt" 2>&1
adb exec-out screencap -p > "$run/application.png"
adb pull /data/tombstones "$run/tombstones" > "$run/tombstone-pull.txt" 2>&1 || true
adb logcat -b crash -d > "$run/crash-logcat.txt"
final_pid=$(adb shell pidof system_server | tr -d '\r')
printf 'after_observation = %s\n' "$final_pid" >> "$run/system-server-pid.toml"
[ "$final_pid" = "$system_pid" ]
printf 'install = "admitted"\nlaunch = "attempted"\n' > "$run/probe-result.toml"
