#!/bin/sh
# Native SDK process orchestration only; all guest state and raw evidence stay local.
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
run_id=${1:?Usage: run-admission.sh RUN_ID [inspect|probe|label|startup|mapping|syscall|native|exclusive|execution|threads|discovery|coverage|groupcontrol|groupmodel|nextcontrol|nextmodel|writecontrol|writemodel|paircontrol|pairmodel|transcriptcontrol|transcriptmodel|spucontrol|spumodel|remainingmodel|remainingcontrol|tailcontrol|tailmodel|loadercontrol|loaderisolated|filesystem|fileaccess|filelabel|loadermodel]}
mode=${2:-inspect}
case "$mode" in inspect|probe|label|startup|mapping|syscall|native|exclusive|execution|threads|discovery|coverage|groupcontrol|groupmodel|nextcontrol|nextmodel|writecontrol|writemodel|paircontrol|pairmodel|transcriptcontrol|transcriptmodel|spucontrol|spumodel|remainingmodel|remainingcontrol|tailcontrol|tailmodel|loadercontrol|loaderisolated|filesystem|fileaccess|filelabel|loadermodel) ;; *) exit 2;; esac
case "$run_id" in ''|*[!a-zA-Z0-9_-]*) echo 'Invalid run ID' >&2; exit 2;; esac
sdk=${ANDROID_SDK_ROOT:?Set ANDROID_SDK_ROOT locally}
timeout_bin=${TIMEOUT_BIN:-gtimeout}
image="$repo/local/guest-images/api25-default-r02/arm64-v8a"
apk="$repo/local/guest-inputs/Sparrow.apk"
manifest="$repo/experiments/guest-baseline/inputs.toml"
admission_manifest="$repo/experiments/guest-admission/inputs.toml"
run="$repo/out/guest-admission/$run_id"
[ ! -e "$run" ] || { echo 'Run directory already exists; use a fresh ID' >&2; exit 2; }
command -v "$timeout_bin" >/dev/null
command -v yq >/dev/null
command -v lsof >/dev/null
for port in 5580 5581 5041 27043; do
    if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
        echo "Required experiment port $port is occupied" >&2; exit 2
    fi
done
mkdir -p "$run"
mkdir "$run/source"
cp "$repo"/tools/guest/* "$run/source/"
cp "$admission_manifest" "$run/source/admission-inputs.toml"
if [ "$mode" = filesystem ] || [ "$mode" = fileaccess ] || [ "$mode" = filelabel ] || [ "$mode" = loadermodel ]; then
    fixture_manifest="$repo/experiments/calibration-filesystem/inputs.toml"
    fixture_copy=calibration-filesystem-inputs.toml
    if [ "$mode" = fileaccess ] || [ "$mode" = filelabel ] || [ "$mode" = loadermodel ]; then
        fixture_manifest="$repo/experiments/calibration-access/inputs.toml"
        fixture_copy=calibration-access-inputs.toml
        if [ "$mode" = filelabel ]; then
            fixture_manifest="$repo/experiments/calibration-access/label-inputs.toml"
        fi
    fi
    if [ "$mode" = loadermodel ]; then
        fixture_manifest="$repo/experiments/calibration-loaders/stock-inputs.toml"
        fixture_copy=calibration-stock-inputs.toml
    fi
    cp "$fixture_manifest" "$run/source/$fixture_copy"
    yq -p toml -o yaml -r '.artifacts[] | [.path, .sha256] | @tsv' "$fixture_manifest" |
    while IFS="$(printf '\t')" read -r path expected; do
        actual=$(shasum -a 256 "$repo/$path"); actual=${actual%% *}
        [ "$actual" = "$expected" ] || { echo "Fixture input mismatch: $path" >&2; exit 2; }
    done
    ramdisk=$(yq -p toml -o yaml -r '.derivative.path' "$fixture_manifest")
    expected=$(yq -p toml -o yaml -r '.derivative.sha256' "$fixture_manifest")
    actual=$(shasum -a 256 "$repo/$ramdisk"); actual=${actual%% *}
    [ "$actual" = "$expected" ] || exit 2
    cp "$repo/$ramdisk" "$run/fixture-ramdisk.img"
fi
expected=$(yq -p toml -o yaml -r '.frida.server_sha256' "$admission_manifest")
actual=$(shasum -a 256 "$repo/local/guest-tools/frida-16.7.19/server"); actual=${actual%% *}
[ "$actual" = "$expected" ] || { echo 'Frida server mismatch' >&2; exit 2; }
[ "$("$repo/local/guest-tools/frida-16.7.19/venv/bin/frida" --version)" = 16.7.19 ]
uv pip freeze --python "$repo/local/guest-tools/frida-16.7.19/venv/bin/python" > "$run/frida-packages.txt"
yq -p toml -o yaml -r '.sdk_files[] | [.path, .sha256] | @tsv' "$admission_manifest" |
while IFS="$(printf '\t')" read -r path expected; do
    actual=$(shasum -a 256 "$sdk/$path"); actual=${actual%% *}
    [ "$actual" = "$expected" ] || { echo "SDK input mismatch: $path" >&2; exit 2; }
done
# Reject changed inputs before starting a guest. Paths in the manifest are relative.
yq -p toml -o yaml -r '.guest_files[] | [.path, .sha256] | @tsv' "$manifest" |
while IFS="$(printf '\t')" read -r path expected; do
    actual=$(shasum -a 256 "$image/$path"); actual=${actual%% *}
    [ "$actual" = "$expected" ] || { echo "Guest input mismatch: $path" >&2; exit 2; }
done
yq -p toml -o yaml -r '.runtime_files[] | [.path, .sha256] | @tsv' "$manifest" |
while IFS="$(printf '\t')" read -r path expected; do
    actual=$(shasum -a 256 "$sdk/$path"); actual=${actual%% *}
    [ "$actual" = "$expected" ] || { echo "Runtime mismatch: $path" >&2; exit 2; }
done
actual=$(shasum -a 256 "$apk"); actual=${actual%% *}
expected=$(yq -p toml -o yaml -r '.apk.sha256' "$manifest")
[ "$actual" = "$expected" ] || { echo 'APK mismatch' >&2; exit 2; }
shasum -a 256 "$manifest" "$0" "$apk" > "$run/input-sha256.txt"
mkdir -p "$run/home" "$run/avds/baseline-api25.avd" "$run/emulator-home"
export ANDROID_USER_HOME="$run/home"
export ANDROID_EMULATOR_HOME="$run/emulator-home"
export ANDROID_AVD_HOME="$run/avds"
export ANDROID_ADB_SERVER_PORT=5041
export ADB_SERVER_SOCKET=tcp:127.0.0.1:5041
export ADB_VENDOR_KEYS="$run/home"
printf 'avd.ini.encoding=UTF-8\npath=%s\ntarget=android-25\n' \
    "$run/avds/baseline-api25.avd" > "$run/avds/baseline-api25.ini"
cat > "$run/avds/baseline-api25.avd/config.ini" <<EOF
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
hw.keyboard=yes
hw.sdCard=no
image.sysdir.1=$image/
tag.id=default
tag.display=Default
EOF
cp "$image/userdata.img" "$run/userdata.img"
adb() { "$timeout_bin" 15 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
emulator_pid=
logcat_pid=
cleanup() {
    if [ -n "$logcat_pid" ]; then
        kill "$logcat_pid" 2>/dev/null || true
        wait "$logcat_pid" 2>/dev/null || true
    fi
    if [ -n "$emulator_pid" ]; then
        adb emu kill >> "$run/cleanup.log" 2>&1 || true
        kill "$emulator_pid" 2>/dev/null || true
        wait "$emulator_pid" 2>/dev/null || true
    fi
    "$timeout_bin" 10 "$sdk/platform-tools/adb" -P 5041 kill-server >> "$run/cleanup.log" 2>&1 || true
}
trap cleanup EXIT
trap 'exit 130' INT TERM
started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
"$timeout_bin" 15 "$sdk/platform-tools/adb" -P 5041 start-server > "$run/adb-server.log" 2>&1
set -- "$sdk/emulator/emulator" -avd baseline-api25 -sysdir "$image" \
    -data "$run/userdata.img" -cache "$run/cache.img" -port 5580 \
    -no-window -no-snapshot -no-boot-anim -no-audio -no-metrics \
    -gpu swiftshader -memory 2048 -cores 2 -verbose -show-kernel
if [ "$mode" = filesystem ] || [ "$mode" = fileaccess ] || [ "$mode" = filelabel ] || [ "$mode" = loadermodel ]; then
    set -- "$@" -ramdisk "$run/fixture-ramdisk.img"
fi
printf '%s\n' "$@" > "$run/emulator-argv.txt"
"$timeout_bin" 600 "$@" > "$run/emulator.log" 2>&1 &
emulator_pid=$!
boot=timed_out
install=not_reached
launch=not_reached
graphics=not_reached
emulator_exit=not_observed
inspection=not_reached
deadline=$(( $(date +%s) + 180 ))
while [ "$(date +%s)" -lt "$deadline" ]; do
    if ! kill -0 "$emulator_pid" 2>/dev/null; then
        emulator_exit=0
        wait "$emulator_pid" || emulator_exit=$?
        emulator_pid=
        boot=emulator_exited
        break
    fi
    state=$(adb get-state 2>/dev/null || true)
    if [ "$state" = device ]; then
        if [ -z "$logcat_pid" ]; then
            "$timeout_bin" 580 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 \
                logcat -b all -v threadtime > "$run/logcat-stream.txt" 2>&1 &
            logcat_pid=$!
        fi
        completed=$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)
        if [ "$completed" = 1 ]; then boot=completed; break; fi
    fi
    sleep 2
done
adb devices -l > "$run/adb-devices.txt" 2>&1 || true
if [ "$boot" = completed ]; then
    adb shell getprop > "$run/getprop.txt" 2>&1
    adb shell uname -a > "$run/guest-kernel.txt" 2>&1
    adb shell dumpsys SurfaceFlinger > "$run/surfaceflinger.txt" 2>&1 || true
    if adb exec-out screencap -p > "$run/boot.png" 2> "$run/boot-screenshot-error.txt"; then
        graphics=screenshot_captured
    else graphics=screenshot_failed; fi
    adb pull /system/framework/framework-res.apk "$run/framework-res.apk" \
        > "$run/platform-apk-pull.txt" 2>&1 || true
    if [ -f "$run/framework-res.apk" ]; then
        "$timeout_bin" 20 "$sdk/build-tools/35.0.0/apksigner" verify --print-certs \
            "$run/framework-res.apk" > "$run/platform-signature.txt" 2>&1 || true
    fi
    export ADMISSION_RUN="$run" ADMISSION_REPO="$repo" ADMISSION_MODE="$mode"
    inspection=completed
    helper_mode=$mode
    case "$mode" in filelabel) helper_mode=fileaccess;; esac
    case "$mode" in nextcontrol|writecontrol|paircontrol) helper_mode=groupcontrol;; esac
    case "$mode" in transcriptcontrol) helper_mode=transcriptcontrol;; esac
    case "$mode" in spucontrol) helper_mode=spucontrol;; remainingcontrol) helper_mode=remainingcontrol;; esac
    case "$mode" in startup|mapping|syscall|native|coverage|groupmodel|nextmodel|writemodel|pairmodel|transcriptmodel|spumodel|remainingmodel|tailmodel) helper_mode=label;; esac
    "$run/source/admission-$helper_mode.sh" || inspection=failed
    case "$mode" in loadercontrol|loaderisolated|filesystem|fileaccess|filelabel|loadermodel)
        health_rc=0
        "$run/source/admission-final-health.sh" || health_rc=$?
        printf 'final_health_helper_exit = %s\n' "$health_rc" >> "$run/final-health-status.toml"
        [ "$health_rc" = 0 ] || inspection=failed
        ;;
    esac
    if [ -f "$run/probe-result.toml" ]; then
        install=$(yq -p toml -o yaml -r '.install' "$run/probe-result.toml")
        launch=$(yq -p toml -o yaml -r '.launch' "$run/probe-result.toml")
    fi
fi
adb logcat -b all -d > "$run/logcat-final.txt" 2>&1 || true
finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)
cat > "$run/result.toml" <<EOF
schema_version = "mho900-lab.guest-run/1"
run_id = "$run_id"
started_at = "$started"
finished_at = "$finished"
boot = "$boot"
graphics = "$graphics"
install = "$install"
launch = "$launch"
emulator_exit = "$emulator_exit"
mode = "$mode"
inspection = "$inspection"
EOF
cleanup
emulator_pid=
logcat_pid=
trap - EXIT
for artifact in "$run"/*.txt "$run"/*.log "$run"/*.stderr "$run"/*.png "$run"/*.toml "$run"/*.policy \
    "$run"/*.bin "$run"/*.tsv "$run"/*.jar "$run"/*.odex "$run"/*.apk "$run"/*.xml "$run"/*.elf "$run"/seapp_contexts \
    "$run"/source/* "$run"/tombstones/* "$run"/fixture-ramdisk.img; do
    [ "$artifact" != "$run/evidence-sha256.txt" ] || continue
    [ -f "$artifact" ] || continue
    shasum -a 256 "$artifact"
done > "$run/evidence-sha256.txt"
cat "$run/result.toml"
[ "$boot" = completed ] && [ "$inspection" = completed ]
