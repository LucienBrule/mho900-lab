#!/bin/sh
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
if [ "${NATIVE_POST_STORE:-0}" = 1 ]; then
    final_sample() {
        rc=$?
        trap - EXIT
        adb shell getenforce > "$run/native-final-enforcing.txt" 2>&1 || true
        adb shell pidof system_server > "$run/native-final-system-server.txt" 2>&1 || true
        exit "$rc"
    }
    trap final_sample EXIT
fi
cp "$repo/local/guest-tools/native-probe/"*.txt "$run/"
cp "$repo/local/guest-tools/native-probe/native-probe" "$run/native-probe.elf"
adb push "$run/native-probe.elf" /data/local/tmp/native-probe > "$run/native-push.txt"
adb shell chmod 755 /data/local/tmp/native-probe
for which in 0 1 2 3; do
    rc=0
    adb shell "/data/local/tmp/native-probe control $which" > "$run/native-control-$which.toml" 2>&1 || rc=$?
    printf 'exit_code = %s\n' "$rc" > "$run/native-control-$which-status.toml"
    [ "$rc" = 0 ] || exit 3
done
command=stock
word=${NATIVE_TEST_WORD:-}
pair=${NATIVE_TWO_WORD:-0}
post_store=${NATIVE_POST_STORE:-0}
case "$pair" in 0|1) ;; *) exit 2;; esac
case "$post_store" in 0|1) ;; *) exit 2;; esac
if [ "$post_store" = 1 ]; then
    [ "$pair" = 0 ] && [ -z "$word" ] || exit 2
    command=stock-post-store
    cp "$repo/experiments/xdma-post-store/fixture.toml" "$run/native-post-store-fixture.toml"
    cp "$repo/experiments/xdma-post-store/inventory-profile.toml" "$run/native-inventory-profile.toml"
    cp "$repo/experiments/guest-execution-stop/profile.toml" "$run/native-execution-profile.toml"
    [ "$(adb shell uname -r | tr -d '\r')" = '3.18.91+' ] || exit 3
    rc=0
    adb shell '/data/local/tmp/native-probe control-post-store 0' > "$run/native-post-store-control.toml" 2>&1 || rc=$?
    printf 'exit_code = %s\n' "$rc" > "$run/native-post-store-control-status.toml"
    [ "$rc" = 0 ] || exit 3
    rc=0
    adb shell '/data/local/tmp/native-probe control-post-store 1' > "$run/native-post-store-negative.toml" 2>&1 || rc=$?
    printf 'exit_code = %s\n' "$rc" > "$run/native-post-store-negative-status.toml"
    [ "$rc" = 78 ] || exit 3
    kotlin "$run/source/VerifyPostStore.main.kts" "$run" controls > "$run/native-post-store-controls-verification.toml"
fi
if [ "$pair" = 1 ]; then
    [ -z "$word" ] || exit 2
    command=stock-pair
    cp "$repo/experiments/xdma-two-word/fixture.toml" "$run/native-pair-fixture.toml"
    cp "$repo/experiments/xdma-two-word/profile.toml" "$run/native-pair-profile.toml"
    release=$(adb shell uname -r | tr -d '\r')
    [ "$release" = "$(yq -p toml -r '.guest_release' "$run/native-pair-profile.toml")" ] || exit 3
    adb shell '/data/local/tmp/native-probe control-pair 0' > "$run/native-pair-control.toml" 2>&1
    rc=0
    adb shell '/data/local/tmp/native-probe control-pair 1' > "$run/native-pair-negative.toml" 2>&1 || rc=$?
    printf 'exit_code = %s\n' "$rc" > "$run/native-pair-negative-status.toml"
    [ "$rc" = 78 ] || exit 3
    kotlin "$run/source/VerifyPairControls.main.kts" "$run" > "$run/native-pair-controls-verification.toml"
fi
if [ -n "$word" ]; then
    case "$word" in 0|11223344) ;; *) exit 2;; esac
    command=stock-step
    adb shell "/data/local/tmp/native-probe control-step $word" > "$run/native-step-control.toml" 2>&1
    printf 'word = "0x%s"\n' "$word" > "$run/native-test-word.toml"
fi
pid=$(adb shell pidof com.rigol.scope | tr -d '\r')
case "$pid" in ''|*[!0-9]*) exit 2;; esac
printf 'pid = %s\n' "$pid" > "$run/native-app-pid.toml"
adb shell "cat /proc/$pid/cmdline; cat /proc/$pid/attr/current; cat /proc/$pid/maps" > "$run/native-before.txt"
if [ "$pair" = 1 ] || [ "$post_store" = 1 ]; then
    adb pull /system/lib64/libc.so "$run/native-libc.so" > "$run/native-libc-pull.txt" 2>&1
    shasum -a 256 "$run/native-libc.so" > "$run/native-libc-sha256.txt"
    adb shell "ls /proc/$pid/task" > "$run/native-thread-ids.txt"
fi
actual=$(unzip -p "$run/installed.apk" lib/arm64-v8a/libscope-auklet.so | shasum -a 256); actual=${actual%% *}
[ "$actual" = 4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e ]
# The pinned APK's stored ELF starts at ZIP data offset 0xf05000; verifier derives it independently.
base=$(sed -n 's/^\([0-9a-f]*\)-.* r-xp 00f05000 .*com.rigol.scope.*\/base.apk$/\1/p' "$run/native-before.txt")
case "$base" in ''|*[!0-9a-f]*) exit 2;; esac
if [ "$post_store" = 1 ]; then
    adb shell 'test ! -e /dev/xdma0_bypass && rm -f /data/local/tmp/native-events.toml /data/local/tmp/native-status.toml /data/local/tmp/native-pid' \
        > "$run/native-marker-reset.txt" 2>&1
fi
adb shell "/data/local/tmp/native-probe $command $pid $base $word >/data/local/tmp/native-events.toml 2>&1 & tracer=\$!; echo \$tracer >/data/local/tmp/native-pid; wait \$tracer; rc=\$?; echo exit_code = \$rc >/data/local/tmp/native-status.toml" \
    > "$run/native-command.txt" 2>&1 &
command_pid=$!
ready=false
for attempt in 1 2 3 4 5; do
    adb shell cat /data/local/tmp/native-events.toml > "$run/native-readiness.toml" 2>&1 || true
    if grep -q 'kind = "ready"' "$run/native-readiness.toml"; then ready=true; break; fi
    sleep 1
done
if [ "$ready" = true ]; then
    adb shell 'test ! -e /dev/xdma0_bypass && ln -s /dev/null /dev/xdma0_bypass; ls -lZ /dev/xdma0_bypass' \
        > "$run/native-device.txt" 2>&1
    for attempt in 1 2 3 4 5 6 7 8 9 10; do
        if adb shell test -f /data/local/tmp/native-status.toml; then break; fi
        sleep 1
    done
fi
adb shell 'p=$(cat /data/local/tmp/native-pid); if [ -r /proc/$p/cmdline ] && grep -q native-probe /proc/$p/cmdline; then kill -9 $p; fi; rm -f /dev/xdma0_bypass' \
    > "$run/native-cleanup.txt" 2>&1 || true
wait "$command_pid" || true
adb pull /data/local/tmp/native-events.toml "$run/native-events.toml" > "$run/native-events-pull.txt" 2>&1
adb pull /data/local/tmp/native-status.toml "$run/native-status.toml" > "$run/native-status-pull.txt" 2>&1
if [ "$post_store" = 1 ]; then
    adb pull /data/local/tmp/native-probe "$run/native-executed.elf" > "$run/native-executed-pull.txt" 2>&1
    cmp "$run/native-probe.elf" "$run/native-executed.elf"
fi
adb shell 'getenforce' > "$run/native-enforcing.txt"
sleep 2
if [ "$post_store" = 1 ]; then
    grep -qx 'exit_code = 0' "$run/native-status.toml"
fi
