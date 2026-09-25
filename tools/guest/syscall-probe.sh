#!/bin/sh
# Native observer only; never inject into the stock application.
set -eu
run=${ADMISSION_RUN:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
pid=$(adb shell pidof com.rigol.scope | tr -d '\r')
case "$pid" in ''|*[!0-9]*) exit 2;; esac
printf 'pid = %s\n' "$pid" > "$run/syscall-app-pid.toml"
adb shell "cat /proc/$pid/maps; cat /proc/$pid/status" > "$run/syscall-before.txt"
adb shell 'getenforce; command -v strace; ls -lZ /system/bin/strace /system/xbin/strace' \
    > "$run/syscall-tool-inventory.txt" 2>&1 || true
observer=$(adb shell 'command -v strace' | tr -d '\r')
case "$observer" in /system/bin/strace|/system/xbin/strace) ;; *)
    printf 'outcome = "observer unavailable"\n' > "$run/syscall-outcome.toml"; exit 0;; esac
adb pull "$observer" "$run/strace" > "$run/syscall-tool-pull.txt" 2>&1
adb shell 'strace -V' > "$run/syscall-tool-version.txt" 2>&1
adb shell 'strace -tt -i -o /data/local/tmp/control.trace /system/bin/cat /dev/null' \
    > "$run/syscall-control-status.txt" 2>&1
adb pull /data/local/tmp/control.trace "$run/syscall-control.txt" > "$run/syscall-control-pull.txt" 2>&1
adb shell "strace -f -tt -i -e trace=openat,mmap,munmap,close,exit_group -o /data/local/tmp/stock.trace -p $pid >/data/local/tmp/strace-status.txt 2>&1 & echo \$! >/data/local/tmp/strace-pid" \
    > "$run/syscall-attach.txt" 2>&1
sleep 2
adb shell "cat /proc/$pid/status" > "$run/syscall-attached-status.txt"
if ! grep -Eq '^TracerPid:[[:space:]]+[1-9][0-9]*' "$run/syscall-attached-status.txt"; then
    printf 'outcome = "observer attach failed"\n' > "$run/syscall-outcome.toml"
else
    adb shell 'test ! -e /dev/xdma0_bypass && ln -s /dev/null /dev/xdma0_bypass && ls -lZ /dev/xdma0_bypass /dev/null' \
        > "$run/syscall-device.txt" 2>&1
    sleep 12
    printf 'outcome = "observation completed"\n' > "$run/syscall-outcome.toml"
fi
adb shell 'kill $(cat /data/local/tmp/strace-pid) 2>/dev/null; rm -f /dev/xdma0_bypass' \
    > "$run/syscall-cleanup.txt" 2>&1 || true
adb pull /data/local/tmp/stock.trace "$run/syscall-stock.txt" > "$run/syscall-trace-pull.txt" 2>&1 || true
adb pull /data/local/tmp/strace-status.txt "$run/syscall-status.txt" > "$run/syscall-status-pull.txt" 2>&1 || true
adb shell 'getenforce' > "$run/syscall-enforcing.txt"
