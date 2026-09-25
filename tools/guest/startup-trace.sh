#!/bin/sh
# Observational snapshots only; debuggerd and SIGQUIT may briefly perturb timing.
set -eu
run=${ADMISSION_RUN:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
app_pid=$(adb shell pidof com.rigol.scope | tr -d '\r')
case "$app_pid" in ''|*[!0-9]*) echo 'Expected one surviving stock process' >&2; exit 2;; esac
adb shell "cat /proc/$app_pid/cmdline; cat /proc/$app_pid/attr/current; cat /proc/$app_pid/status" \
    > "$run/startup-process.txt"
adb shell "cat /proc/$app_pid/maps" > "$run/startup-maps.txt"
adb shell "ls -l /proc/$app_pid/fd; ls -lZ /dev/xdma* /dev/dma* /dev/spi*; ls -l /data" \
    > "$run/startup-files.txt" 2>&1 || true
for sample in 1 2; do
    adb shell "for task in /proc/$app_pid/task/*; do echo \"THREAD \$task\"; cat \"\$task/comm\" \"\$task/wchan\" \"\$task/syscall\"; done" \
        > "$run/startup-threads-$sample.txt" 2>&1 || true
    rc=0
    adb shell "debuggerd -b $app_pid" > "$run/startup-native-$sample.txt" 2>&1 || rc=$?
    printf 'exit_code = %s\n' "$rc" > "$run/startup-native-$sample.toml"
    adb exec-out screencap -p > "$run/startup-$sample.png"
    if [ "$sample" = 1 ]; then sleep 15; fi
done
adb shell "kill -3 $app_pid" > "$run/startup-sigquit.txt" 2>&1
sleep 2
adb shell cat /data/anr/traces.txt > "$run/startup-java.txt" 2>&1 || true
adb shell "cat /proc/$app_pid/maps" > "$run/startup-final-maps.txt"
adb shell pidof com.rigol.scope > "$run/startup-final-pid.txt"
