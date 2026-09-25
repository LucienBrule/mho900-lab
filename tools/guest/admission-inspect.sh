#!/bin/sh
# Diagnostic access is confined to the private emulator selected by its parent.
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
frida_home=${ADMISSION_FRIDA_HOME:-"$repo/local/guest-tools/frida-16.7.19"}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 20 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
adb root > "$run/adb-root.txt" 2>&1
adb wait-for-device
adb shell 'id; getenforce; getprop ro.build.fingerprint; ls -l /system/framework/services.jar; ls /system/framework/arm64; ls /system/framework/oat/arm64; ls /data/dalvik-cache/arm64; command -v oatdump' \
    > "$run/framework-inventory.txt" 2>&1
adb pull /system/framework/services.jar "$run/services.jar" > "$run/framework-pull.txt" 2>&1
adb pull /system/framework/oat/arm64/services.odex "$run/services.odex" >> "$run/framework-pull.txt" 2>&1
adb shell 'oatdump --oat-file=/system/framework/oat/arm64/services.odex --class-filter=PackageManagerService --method-filter=verifySignaturesLP' \
    > "$run/verify-signatures-oatdump.txt" 2>&1 || true
shasum -a 256 "$run/services.jar" "$run/services.odex" > "$run/framework-sha256.txt"
actual=$(shasum -a 256 "$run/services.odex"); actual=${actual%% *}
expected=$(yq -p toml -o yaml -r '.services_odex_sha256' "$repo/experiments/guest-admission/inputs.toml")
[ "$actual" = "$expected" ]
adb pull /seapp_contexts "$run/seapp_contexts" > "$run/selinux-config-pull.txt" 2>&1
adb pull /system/etc/security/mac_permissions.xml "$run/mac_permissions.xml" >> "$run/selinux-config-pull.txt" 2>&1
adb exec-out cat /sys/fs/selinux/policy > "$run/selinux-before.policy"
adb push "$frida_home/server" /data/local/tmp/admission-frida \
    > "$run/frida-push.txt" 2>&1
adb shell 'chmod 700 /data/local/tmp/admission-frida; /data/local/tmp/admission-frida --version' \
    > "$run/frida-version.txt" 2>&1
adb shell 'nohup /data/local/tmp/admission-frida --disable-preload --ignore-crashes -l 127.0.0.1:27042 >/data/local/tmp/frida-server.txt 2>&1 </dev/null &' \
    > "$run/frida-server.txt" 2>&1
sleep 3
adb shell 'ps; cat /data/local/tmp/frida-server.txt; cat /proc/net/tcp' > "$run/server-state.txt" 2>&1
adb forward tcp:27043 tcp:27042 > "$run/frida-forward.txt" 2>&1
system_pid=$(adb shell pidof system_server | tr -d '\r')
gtimeout -k 2 35 "$frida_home/venv/bin/frida" -H 127.0.0.1:27043 \
    -p "$system_pid" -l "$run/source/inspect-framework.js" -q -t 8 --no-auto-reload --exit-on-error \
    > "$run/frida-inspection.txt" 2>&1
adb shell getenforce > "$run/selinux-after.txt"
adb exec-out cat /sys/fs/selinux/policy > "$run/selinux-after.policy"
shasum -a 256 "$run"/*.policy > "$run/selinux-sha256.txt"
