#!/bin/sh
# Specimen-derived native baseline in a disposable, host-loopback-only guest.
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
run_id=${1:?Usage: run-entitlement-baseline.sh RUN_ID FIXTURE_DIR CONTROLLER.py SOURCE.js}
fixture_arg=${2:?}
controller_arg=${3:?}
js_arg=${4:?}
[ "$#" = 4 ]
case "$run_id" in ''|*[!a-zA-Z0-9_-]*) exit 2;; esac
sdk=${ANDROID_SDK_ROOT:?Set ANDROID_SDK_ROOT locally}
frida_home=${ENTITLEMENT_FRIDA_HOME:-"$repo/local/guest-tools/frida-16.7.19-r02"}
python="$frida_home/venv/bin/python"
timeout_bin=${TIMEOUT_BIN:-gtimeout}
fixture=$(CDPATH= cd -- "$fixture_arg" && pwd)
run="$repo/out/specimen-entitlement/$run_id"
[ ! -e "$run" ]
[ -d "$fixture/lib" ] && [ -d "$fixture/rigol" ]
[ -f "$controller_arg" ] && [ -f "$js_arg" ]
for port in 5043 5582 5583 27045; do
    if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
        echo "Required guest-only port $port is occupied" >&2; exit 2
    fi
done
umask 077
mkdir -p "$run/source" "$run/home" "$run/emulator-home" "$run/avds/baseline-api25.avd"
cp "$0" "$repo/tools/guest/offline-loopback.sb" "$repo/tools/guest/test-offline-network.py" \
    "$repo/tools/guest/entitlement-files.py" "$repo/tools/guest/verify-entitlement-journal.py" "$repo/tools/guest/stage-userdata.sh" "$run/source/"
cp "$controller_arg" "$run/source/entitlement-controller.py"
cp "$js_arg" "$run/source/entitlement.js"
cp "$repo/experiments/guest-baseline/inputs.toml" "$run/source/guest-inputs.toml"
cp "$repo/experiments/guest-admission/inputs.toml" "$run/source/admission-inputs.toml"
profile="$run/source/offline-loopback.sb"
"$python" "$run/source/test-offline-network.py" "$profile" > "$run/network-control.toml" 2> "$run/network-control.stderr"
"$python" "$run/source/entitlement-files.py" "$fixture" > "$run/fixture-before.toml"
cp -pR "$fixture" "$run/fixture"
"$python" "$run/source/entitlement-files.py" "$run/fixture" > "$run/fixture-copy.toml"
cmp "$run/fixture-before.toml" "$run/fixture-copy.toml"
image="$repo/local/guest-images/api25-default-r02/arm64-v8a"
check_hash() {
    actual=$(shasum -a 256 "$1"); actual=${actual%% *}
    [ "$actual" = "$2" ] || { echo "Input hash mismatch: $3" >&2; exit 2; }
}
yq -p toml -o yaml -r '.guest_files[] | [.path,.sha256] | @tsv' "$run/source/guest-inputs.toml" |
while IFS="$(printf '\t')" read -r path expected; do check_hash "$image/$path" "$expected" "$path"; done
yq -p toml -o yaml -r '.runtime_files[] | [.path,.sha256] | @tsv' "$run/source/guest-inputs.toml" |
while IFS="$(printf '\t')" read -r path expected; do check_hash "$sdk/$path" "$expected" "$path"; done
check_hash "$frida_home/server" "$(yq -p toml -o yaml -r '.frida.server_sha256' "$run/source/admission-inputs.toml")" frida-server
check_hash "$run/fixture/lib/libscope-auklet.so" 4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e stock-auklet
check_hash "$run/fixture/lib/libc++_shared.so" 28e7a3a306d7fc222c62abe08741cfcba38c3f336216c4563726bf985ae3cfd6 stock-cxx
check_hash "$run/fixture/lib/libfftw3f.so" 52600ef8e0f4c10a97605f8f16c0fb3836b7ac20bcc2a3442647d62426c5ba9c stock-fftw
cp "$repo/tools/guest/VerifyFridaEnvironment.main.kts" "$run/source/"
cp "$repo/out/stock-adc-sequence-preparation/frida-environment-files.toml" "$run/source/"
kotlin "$run/source/VerifyFridaEnvironment.main.kts" "$frida_home" "$run/source/frida-environment-files.toml" > "$run/frida-tooling.toml"
"$python" --version > "$run/python-version.txt"
"$python" -c 'from importlib.metadata import version; print("frida = " + version("frida")); print("frida_tools = " + version("frida-tools"))' > "$run/frida-versions.txt"
cp "$frida_home/server" "$run/frida-server"
ramdisk="$run/fixture/ramdisk.img"
if [ ! -f "$ramdisk" ]; then
    ramdisk="$run/ramdisk.img"
    cp "$repo/out/calibration-filesystem/build-04/ramdisk.img" "$ramdisk"
fi
check_hash "$ramdisk" 98b4925f73aa77cd21a6d4e2a3f384056dba8b2d379162ad2c02f55f3a071398 empty-rigol-ramdisk
shasum -a 256 "$ramdisk" "$run/source/"* "$python" "$run/frida-server" > "$run/input-sha256.txt"
"$run/source/stage-userdata.sh" "$image/userdata.img" "$run/userdata.img" "$run/userdata-staging.toml" 2097152
export ANDROID_USER_HOME="$run/home" ANDROID_EMULATOR_HOME="$run/emulator-home" ANDROID_AVD_HOME="$run/avds"
export ANDROID_ADB_SERVER_PORT=5043 ADB_SERVER_SOCKET=tcp:127.0.0.1:5043 ADB_VENDOR_KEYS="$run/home"
export ADB_MDNS=0 ADB_MDNS_AUTO_CONNECT=0
export ENTITLEMENT_RUN="$run" ENTITLEMENT_ADB_PORT=5043 ENTITLEMENT_SERIAL=emulator-5582
export ENTITLEMENT_FRIDA_ENDPOINT=127.0.0.1:27045 ENTITLEMENT_GUEST_ROOT=/data/local/tmp/entitlement
# Every network-capable experiment process gets the same inherited child policy.
offline() { /usr/bin/sandbox-exec -f "$profile" "$@"; }
adb() { offline "$timeout_bin" -k 2 20 "$sdk/platform-tools/adb" -P 5043 -s emulator-5582 "$@"; }
emulator_pid=
logcat_pid=
boot=false
fixture_staged=false
phase=prepared
controller_rc=not_run
controller_started=false
started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
cleanup() {
    result=$?
    original_exit=$result
    trap - EXIT INT TERM
    set +e
    if [ "$boot" = true ]; then
        adb shell 'pidof system_server; getenforce; id; cat /proc/mounts; ps' > "$run/final-health.txt" 2>&1
        adb shell getenforce > "$run/final-enforcing.txt" 2>&1
        adb shell pidof system_server > "$run/final-system-server.txt" 2>&1
        if [ -f "$run/initial-enforcing.txt" ]; then cmp "$run/initial-enforcing.txt" "$run/final-enforcing.txt" || result=1; fi
        if [ -f "$run/initial-system-server.txt" ]; then cmp "$run/initial-system-server.txt" "$run/final-system-server.txt" || result=1; fi
        adb exec-out cat /sys/fs/selinux/policy > "$run/selinux-after.policy" 2> "$run/selinux-after.stderr"
        if [ "$fixture_staged" = true ]; then
        adb pull /data/local/tmp/entitlement/rigol "$run/after-rigol" > "$run/after-pull.txt" 2>&1
        pull_rc=$?
        printf 'after_pull_exit = %s\n' "$pull_rc" > "$run/final-status.toml"
        if [ "$pull_rc" = 0 ]; then
            "$python" "$run/source/entitlement-files.py" "$run/after-rigol" > "$run/after-rigol.toml" || result=1
        else result=1; fi
        fi
        if [ "$controller_started" = true ]; then
            adb pull /data/local/tmp/entitlement/events.jsonl "$run/guest-events.jsonl" > "$run/journal-pull.txt" 2>&1
            journal_rc=$?
            printf 'journal_required = true\njournal_pull_exit = %s\n' "$journal_rc" > "$run/journal-status.toml"
            if [ "$journal_rc" = 0 ] && [ -s "$run/guest-events.jsonl" ]; then
                printf 'journal_present_nonempty = true\n' >> "$run/journal-status.toml"
            else
                printf 'journal_present_nonempty = false\n' >> "$run/journal-status.toml"
                result=1
            fi
            adb logcat -b crash -d > "$run/crash-logcat.txt" 2>&1
            printf 'crash_logcat_exit = %s\n' "$?" >> "$run/journal-status.toml"
            adb shell 'ls -l /data/tombstones; cat /data/local/tmp/entitlement-frida.log' > "$run/fault-context.txt" 2>&1
            printf 'fault_context_exit = %s\n' "$?" >> "$run/journal-status.toml"
        else
            printf 'journal_required = false\n' > "$run/journal-status.toml"
        fi
        adb logcat -b all -d > "$run/logcat-final.txt" 2>&1
        adb shell 'kill $(pidof entitlement-frida)' > "$run/frida-stop.txt" 2>&1
    fi
    if [ -n "$logcat_pid" ]; then kill "$logcat_pid" 2>/dev/null; wait "$logcat_pid"; fi
    if [ -n "$emulator_pid" ]; then
        adb emu kill > "$run/emulator-stop.txt" 2>&1
        kill "$emulator_pid" 2>/dev/null
        wait "$emulator_pid"
        printf 'emulator_wait_exit = %s\n' "$?" >> "$run/final-status.toml"
    fi
    offline "$timeout_bin" -k 2 10 "$sdk/platform-tools/adb" -P 5043 kill-server > "$run/adb-stop.txt" 2>&1
    "$python" "$run/source/entitlement-files.py" "$fixture" > "$run/fixture-final.toml"
    cmp "$run/fixture-before.toml" "$run/fixture-final.toml" || result=1
    "$python" "$run/source/entitlement-files.py" "$run/source" > "$run/source-final.toml"
    : > "$run/evidence-sha256.txt"
    for artifact in "$run"/*.txt "$run"/*.toml "$run"/*.stderr "$run"/*.stdout "$run"/*.log "$run"/*.policy "$run"/*.jsonl; do
        [ -f "$artifact" ] || continue
        [ "$artifact" != "$run/evidence-sha256.txt" ] || continue
        [ "$artifact" != "$run/result.toml" ] || continue
        shasum -a 256 "$artifact" >> "$run/evidence-sha256.txt" || result=1
    done
    cat > "$run/result.toml" <<RESULT
schema_version = "mho900-lab.entitlement-baseline-run/1"
run_id = "$run_id"
started_at = "$started"
finished_at = "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
boot_completed = $boot
stopped_phase = "$phase"
controller_exit = "$controller_rc"
runner_exit = $result
original_exit = $original_exit
physical_contact = false
RESULT
    shasum -a 256 "$run/result.toml" >> "$run/evidence-sha256.txt" || result=1
    cat "$run/result.toml"
    exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT TERM
printf 'avd.ini.encoding=UTF-8\npath=%s\ntarget=android-25\n' "$run/avds/baseline-api25.avd" > "$run/avds/baseline-api25.ini"
cat > "$run/avds/baseline-api25.avd/config.ini" <<CONFIG
AvdId=baseline-api25
avd.ini.encoding=UTF-8
abi.type=arm64-v8a
hw.cpu.arch=arm64
hw.cpu.ncore=2
hw.ramSize=2048
hw.lcd.width=1280
hw.lcd.height=800
hw.lcd.density=160
hw.gpu.enabled=yes
hw.gpu.mode=swiftshader
hw.sdCard=no
image.sysdir.1=$image/
tag.id=default
CONFIG
phase=adb-start
offline "$timeout_bin" -k 2 15 "$sdk/platform-tools/adb" -P 5043 --one-device emulator-5582 start-server > "$run/adb-server.log" 2>&1
mdns_rc=0
offline "$timeout_bin" -k 2 10 "$sdk/platform-tools/adb" -P 5043 mdns check > "$run/adb-mdns.txt" 2>&1 || mdns_rc=$?
printf 'mdns_check_exit = %s\n' "$mdns_rc" > "$run/adb-mdns-status.toml"
grep -q '^ERROR: mdns discovery disabled' "$run/adb-mdns.txt"
phase=emulator-start
set -- "$sdk/emulator/emulator" -avd baseline-api25 -sysdir "$image" -ramdisk "$ramdisk" \
    -data "$run/userdata.img" -cache "$run/cache.img" -port 5582 -no-window -no-snapshot \
    -no-boot-anim -no-audio -no-metrics -gpu swiftshader -memory 2048 -cores 2 -verbose -show-kernel
printf '%s\n' "$@" > "$run/emulator-argv.txt"
offline "$timeout_bin" -k 10 540 "$@" > "$run/emulator.log" 2>&1 &
emulator_pid=$!
phase=boot
end=$(( $(date +%s) + 180 ))
while [ "$(date +%s)" -lt "$end" ]; do
    kill -0 "$emulator_pid"
    if [ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)" = 1 ]; then boot=true; break; fi
    sleep 2
done
[ "$boot" = true ]
adb root > "$run/adb-root.txt" 2>&1
adb wait-for-device
adb shell 'id; getprop; uname -a; cat /proc/mounts' > "$run/guest-baseline.txt" 2>&1
adb shell getenforce > "$run/initial-enforcing.txt"
adb shell pidof system_server > "$run/initial-system-server.txt"
[ "$(tr -d '\r\n' < "$run/initial-enforcing.txt")" = Enforcing ]
offline "$sdk/platform-tools/adb" -P 5043 -s emulator-5582 logcat -b all -v threadtime > "$run/logcat-stream.log" 2>&1 &
logcat_pid=$!
phase=fixture
adb shell 'test ! -e /data/local/tmp/entitlement && test -d /rigol && mkdir /data/local/tmp/entitlement'
adb push "$run/fixture/lib" /data/local/tmp/entitlement/lib > "$run/lib-push.txt" 2>&1
adb push "$run/fixture/rigol" /data/local/tmp/entitlement/rigol > "$run/rigol-push.txt" 2>&1
fixture_staged=true
adb shell 'mount -o bind /data/local/tmp/entitlement/rigol /rigol && cat /proc/mounts && ls -ldZ /rigol /rigol/data' > "$run/bind-mount.txt" 2>&1
adb pull /rigol "$run/before-rigol" > "$run/before-pull.txt" 2>&1
"$python" "$run/source/entitlement-files.py" "$run/before-rigol" > "$run/before-rigol.toml"
adb pull /data/local/tmp/entitlement/lib "$run/guest-libs" > "$run/lib-roundtrip.txt" 2>&1
for name in libc++_shared.so libfftw3f.so libscope-auklet.so; do cmp "$run/fixture/lib/$name" "$run/guest-libs/$name"; done
"$python" "$run/source/entitlement-files.py" "$run/guest-libs" > "$run/guest-libs.toml"
adb exec-out cat /sys/fs/selinux/policy > "$run/selinux-before.policy"
phase=instrumentation
adb push "$run/frida-server" /data/local/tmp/entitlement-frida > "$run/frida-push.txt" 2>&1
adb shell 'chmod 700 /data/local/tmp/entitlement-frida; nohup /data/local/tmp/entitlement-frida --disable-preload --ignore-crashes -l 127.0.0.1:27042 >/data/local/tmp/entitlement-frida.log 2>&1 </dev/null &' > "$run/frida-start.txt" 2>&1
adb forward tcp:27045 tcp:27042 > "$run/frida-forward.txt" 2>&1
sleep 2
adb shell 'ps; cat /data/local/tmp/entitlement-frida.log' > "$run/frida-state.txt" 2>&1
phase=controller
controller_started=true
controller_rc=0
offline "$timeout_bin" -k 5 90 "$python" "$run/source/entitlement-controller.py" "$run/source/entitlement.js" \
    > "$run/controller.stdout" 2> "$run/controller.stderr" || controller_rc=$?
phase=controller-complete
exit "$controller_rc"
