#!/bin/sh
# Native SDK process orchestration only; all guest state and raw evidence stay local.
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
run_id=${1:?Usage: run-admission.sh RUN_ID [inspect|probe|label|startup|mapping|syscall|native|exclusive|execution|threads|discovery|coverage|groupcontrol|groupmodel|nextcontrol|nextmodel|writecontrol|writemodel|paircontrol|pairmodel|transcriptcontrol|transcriptmodel|spucontrol|spumodel|remainingmodel|remainingcontrol|tailcontrol|tailmodel|loadercontrol|loaderisolated|filesystem|fileaccess|filelabel|loadermodel|adcinputcontrol|adcinputmodel|adcsequencecontrol|adcsequencemodel]}
mode=${2:-inspect}
case "$mode" in inspect|probe|label|startup|mapping|syscall|native|exclusive|execution|threads|discovery|coverage|groupcontrol|groupmodel|nextcontrol|nextmodel|writecontrol|writemodel|paircontrol|pairmodel|transcriptcontrol|transcriptmodel|spucontrol|spumodel|remainingmodel|remainingcontrol|tailcontrol|tailmodel|loadercontrol|loaderisolated|filesystem|fileaccess|filelabel|loadermodel|adcinputcontrol|adcinputmodel|adcsequencecontrol|adcsequencemodel) ;; *) exit 2;; esac
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
if [ "$mode" = adcsequencemodel ]; then
    sequence_manifest=${ADMISSION_ADC_SEQUENCE_STOCK_INPUTS:?Set ADMISSION_ADC_SEQUENCE_STOCK_INPUTS to the frozen stock manifest}
    [ "$(yq -p toml -o yaml -r '.run_id' "$sequence_manifest")" = "$run_id" ]
    [ "$(yq -p toml -o yaml -r '.mode' "$sequence_manifest")" = "$mode" ]
    cp "$sequence_manifest" "$run/source/adc-sequence-stock-inputs.toml"
    cp "$sequence_manifest" "$run/source/calibration-stock-runtime-inputs.toml"
    yq -p toml -o yaml -r '.artifacts[] | [.path, .sha256, .run_path] | @tsv' "$sequence_manifest" |
    while IFS="$(printf '\t')" read -r artifact_path expected run_path; do
        actual=$(shasum -a 256 "$repo/$artifact_path"); actual=${actual%% *}
        [ "$actual" = "$expected" ] || { echo "Stock sequence input mismatch: $artifact_path" >&2; exit 2; }
        mkdir -p "$(dirname "$run/$run_path")"
        cp "$repo/$artifact_path" "$run/$run_path"
    done
    ADMISSION_FRIDA_HOME=${ADMISSION_FRIDA_HOME:?Set ADMISSION_FRIDA_HOME to the frozen local tool environment}
    export ADMISSION_FRIDA_HOME
fi
if [ "$mode" = adcsequencecontrol ]; then
    sequence_manifest=${ADMISSION_ADC_SEQUENCE_INPUTS:-"$repo/experiments/adc-sequence/control-inputs.toml"}
    [ "$(yq -p toml -o yaml -r '.run_id' "$sequence_manifest")" = "$run_id" ]
    [ "$(yq -p toml -o yaml -r '.mode' "$sequence_manifest")" = "$mode" ]
    cp "$sequence_manifest" "$run/source/adc-sequence-control-inputs.toml"
    yq -p toml -o yaml -r '.artifacts[] | [.path, .sha256, .run_path] | @tsv' "$sequence_manifest" |
    while IFS="$(printf '\t')" read -r artifact_path expected run_path; do
        actual=$(shasum -a 256 "$repo/$artifact_path"); actual=${actual%% *}
        [ "$actual" = "$expected" ] || { echo "Sequence input mismatch: $artifact_path" >&2; exit 2; }
        mkdir -p "$(dirname "$run/$run_path")"
        cp "$repo/$artifact_path" "$run/$run_path"
    done
fi
if [ "$mode" = adcinputcontrol ] || [ "$mode" = adcinputmodel ]; then
    capture_manifest="$repo/experiments/adc-input-capture/stock-inputs.toml"
    capture_copy=adc-input-capture-inputs.toml
    if [ "$mode" = adcinputcontrol ]; then
        capture_manifest="$repo/experiments/adc-input-capture/control-inputs.toml"
        capture_copy=adc-input-capture-control-inputs.toml
    fi
    [ "$(yq -p toml -o yaml -r '.run_id' "$capture_manifest")" = "$run_id" ]
    [ "$(yq -p toml -o yaml -r '.mode' "$capture_manifest")" = "$mode" ]
    cp "$capture_manifest" "$run/source/$capture_copy"
    cp "$repo/experiments/adc-input-capture/decision.toml" "$run/source/adc-input-capture-decision.toml"
    mkdir "$run/adc-parameter-static"
    cp "$repo/experiments/adc-parameter-static/"*.toml "$run/adc-parameter-static/"
    yq -p toml -o yaml -r '.artifacts[] | [.path, .sha256] | @tsv' "$capture_manifest" |
    while IFS="$(printf '\t')" read -r artifact_path expected; do
        actual=$(shasum -a 256 "$repo/$artifact_path"); actual=${actual%% *}
        [ "$actual" = "$expected" ] || { echo "Capture input mismatch: $artifact_path" >&2; exit 2; }
    done
fi
if [ "$mode" = filesystem ] || [ "$mode" = fileaccess ] || [ "$mode" = filelabel ] || [ "$mode" = loadermodel ] || [ "$mode" = adcinputmodel ]; then
    fixture_manifest="$repo/experiments/calibration-filesystem/inputs.toml"
    fixture_copy=calibration-filesystem-inputs.toml
    if [ "$mode" = fileaccess ] || [ "$mode" = filelabel ] || [ "$mode" = loadermodel ]; then
        fixture_manifest="$repo/experiments/calibration-access/inputs.toml"
        fixture_copy=calibration-access-inputs.toml
        if [ "$mode" = filelabel ]; then
            fixture_manifest="$repo/experiments/calibration-access/label-inputs.toml"
        fi
    fi
    if [ "$mode" = loadermodel ] || [ "$mode" = adcinputmodel ]; then
        fixture_manifest=${ADMISSION_LOADER_INPUTS:-"$repo/experiments/calibration-loaders/stock-inputs.toml"}
        [ "$mode" != adcinputmodel ] || fixture_manifest="$capture_manifest"
        fixture_copy=calibration-stock-runtime-inputs.toml
        [ "$(yq -p toml -o yaml -r '.run_id' "$fixture_manifest")" = "$run_id" ] || { echo 'Loader run identity mismatch' >&2; exit 2; }
        # Keep the original prediction identity for its frozen verifier. The
        # runtime manifest separately pins the actual harness and run identity.
        cp "$repo/experiments/calibration-loaders/stock-inputs.toml" "$run/source/calibration-stock-inputs.toml"
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
. "$run/source/admission-tooling.sh"
runner_frida_prerequisites
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
if [ "$mode" = adcinputcontrol ] || [ "$mode" = adcinputmodel ] || [ "$mode" = adcsequencecontrol ] || [ "$mode" = adcsequencemodel ]; then
    "$run/source/stage-userdata.sh" "$image/userdata.img" "$run/userdata.img" "$run/userdata-staging.toml" 2097152
else
    cp "$image/userdata.img" "$run/userdata.img"
fi
adb() { "$timeout_bin" -k 2 15 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
emulator_pid=
logcat_pid=
cleanup() {
    if [ -n "$logcat_pid" ]; then
        kill "$logcat_pid" 2>/dev/null || true
        wait "$logcat_pid" 2>/dev/null || true
    fi
    if [ -n "$emulator_pid" ]; then
        cleanup_rc=0
        adb emu kill >> "$run/cleanup.log" 2>&1 || cleanup_rc=$?
        printf 'emulator_console_exit = %s\n' "$cleanup_rc" >> "$run/cleanup-status.toml"
        cleanup_rc=0
        kill "$emulator_pid" 2>/dev/null || cleanup_rc=$?
        printf 'emulator_signal_exit = %s\n' "$cleanup_rc" >> "$run/cleanup-status.toml"
        cleanup_rc=0
        wait "$emulator_pid" 2>/dev/null || cleanup_rc=$?
        printf 'emulator_wait_exit = %s\n' "$cleanup_rc" >> "$run/cleanup-status.toml"
    fi
    cleanup_rc=0
    "$timeout_bin" -k 2 10 "$sdk/platform-tools/adb" -P 5041 kill-server >> "$run/cleanup.log" 2>&1 || cleanup_rc=$?
    printf 'adb_server_exit = %s\n' "$cleanup_rc" >> "$run/cleanup-status.toml"
}
. "$run/source/admission-runtime.sh"
started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
boot=not_started
install=not_reached
launch=not_reached
graphics=not_reached
emulator_exit=not_observed
inspection=not_reached
health_attempted=false
phase=adb_start
export ADMISSION_RUN="$run" ADMISSION_REPO="$repo" ADMISSION_MODE="$mode"
trap runner_finalize EXIT
trap 'exit 130' INT TERM
"$timeout_bin" 15 "$sdk/platform-tools/adb" -P 5041 start-server > "$run/adb-server.log" 2>&1
set -- "$sdk/emulator/emulator" -avd baseline-api25 -sysdir "$image" \
    -data "$run/userdata.img" -cache "$run/cache.img" -port 5580 \
    -no-window -no-snapshot -no-boot-anim -no-audio -no-metrics \
    -gpu swiftshader -memory 2048 -cores 2 -verbose -show-kernel
if [ "$mode" = filesystem ] || [ "$mode" = fileaccess ] || [ "$mode" = filelabel ] || [ "$mode" = loadermodel ] || [ "$mode" = adcinputmodel ] || [ "$mode" = adcsequencemodel ]; then
    set -- "$@" -ramdisk "$run/fixture-ramdisk.img"
fi
printf '%s\n' "$@" > "$run/emulator-argv.txt"
"$timeout_bin" 600 "$@" > "$run/emulator.log" 2>&1 &
emulator_pid=$!
boot=timed_out
phase=boot_wait
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
    runner_collect_boot
    phase=admission_helper
    inspection=completed
    helper_mode=$mode
    case "$mode" in filelabel) helper_mode=fileaccess;; esac
    case "$mode" in adcinputmodel|adcsequencemodel) helper_mode=loadermodel;; esac
    case "$mode" in nextcontrol|writecontrol|paircontrol) helper_mode=groupcontrol;; esac
    case "$mode" in transcriptcontrol) helper_mode=transcriptcontrol;; esac
    case "$mode" in spucontrol) helper_mode=spucontrol;; remainingcontrol) helper_mode=remainingcontrol;; esac
    case "$mode" in startup|mapping|syscall|native|coverage|groupmodel|nextmodel|writemodel|pairmodel|transcriptmodel|spumodel|remainingmodel|tailmodel) helper_mode=label;; esac
    "$run/source/admission-$helper_mode.sh" || inspection=failed
    runner_health
    if [ -f "$run/probe-result.toml" ]; then
        install=$(yq -p toml -o yaml -r '.install' "$run/probe-result.toml")
        launch=$(yq -p toml -o yaml -r '.launch' "$run/probe-result.toml")
    fi
fi
phase=finished
[ "$boot" = completed ] && [ "$inspection" = completed ]
