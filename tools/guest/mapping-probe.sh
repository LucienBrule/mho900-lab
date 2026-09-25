#!/bin/sh
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
actual=$(unzip -p "$run/installed.apk" lib/arm64-v8a/libscope-auklet.so | shasum -a 256)
actual=${actual%% *}
[ "$actual" = 4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e ]
app_pid=$(adb shell pidof com.rigol.scope | tr -d '\r')
case "$app_pid" in ''|*[!0-9]*) echo 'Expected one stock process' >&2; exit 2;; esac
printf 'pid = %s\n' "$app_pid" > "$run/mapping-app-pid.toml"
adb shell "cat /proc/$app_pid/attr/current; cat /proc/$app_pid/maps" > "$run/mapping-before.txt"
adb shell 'mkdir -p /data/data/com.rigol.scope/files; chown 1000:1000 /data/data/com.rigol.scope/files; restorecon -R /data/data/com.rigol.scope/files' \
    > "$run/mapping-evidence-directory.txt" 2>&1
adb shell 'nohup /data/local/tmp/admission-frida --disable-preload --ignore-crashes -l 127.0.0.1:27042 >/data/local/tmp/frida-mapping-server.txt 2>&1 </dev/null &' \
    > "$run/mapping-server.txt" 2>&1
sleep 2
adb forward tcp:27043 tcp:27042 > "$run/mapping-forward.txt"
rc=0
gtimeout -k 2 70 "$repo/local/guest-tools/frida-16.7.19/venv/bin/frida" -H 127.0.0.1:27043 \
    -p "$app_pid" -l "$run/source/mapping-adapter.js" -q -t 45 --exit-on-error --no-auto-reload \
    > "$run/mapping-hook.txt" 2>&1 || rc=$?
printf 'exit_code = %s\n' "$rc" > "$run/mapping-cli-status.toml"
# The deliberate first-unknown fault terminates the disposable app, not system_server.
adb pull /data/data/com.rigol.scope/files/mapping-events.toml "$run/mapping-events.toml" \
    > "$run/mapping-events-pull.txt" 2>&1 || true
adb shell pidof com.rigol.scope > "$run/mapping-final-pid.txt" 2>&1 || true
adb shell 'kill $(pidof admission-frida)' > "$run/mapping-server-stop.txt" 2>&1 || true
adb shell 'cat /proc/$(pidof zygote64)/maps' > "$run/mapping-zygote-maps.txt"
sleep 2
