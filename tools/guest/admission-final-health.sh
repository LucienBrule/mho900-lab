#!/bin/sh
# Collect each final witness even if another command fails.
set -eu
run=${ADMISSION_RUN:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 15 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
outcome=0
capture() {
    key=$1; file=$2; shift 2
    rc=0
    adb shell "$@" > "$run/$file" 2>&1 || rc=$?
    printf '%s_exit = %s\n' "$key" "$rc" >> "$run/final-health-status.toml"
    [ "$rc" = 0 ] || outcome=1
}
capture pid final-system-server.txt pidof system_server
capture enforcing final-enforcing.txt getenforce
capture processes final-processes.txt ps
capture packages final-packages.txt pm list packages com.rigol.scope
exit "$outcome"
