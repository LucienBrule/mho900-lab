#!/bin/sh
# A single frozen private capture suite. Each arm has independent guest objects.
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
manifest="$run/source/adc-input-capture-control-inputs.toml"
sample_pid() {
    pid=$(adb shell pidof system_server | tr -d '\r')
    case "$pid" in ''|*[!0-9]*) return 1;; esac
    printf '%s = %s\n' "$1" "$pid" >> "$run/adcinput-system-server.toml"
}
sample_pid before
system_pid=$pid
outcome=0
finalize() {
    rc=$?
    trap - EXIT
    adb shell getenforce > "$run/adcinput-final-enforcing.txt" 2>&1 || rc=1
    adb shell pm list packages com.rigol.scope > "$run/adcinput-final-packages.txt" 2>&1 || rc=1
    adb shell ps > "$run/adcinput-processes-after.txt" 2>&1 || rc=1
    sample_pid after || rc=1
    [ "$pid" = "$system_pid" ] || rc=1
    [ ! -s "$run/adcinput-final-packages.txt" ] || rc=1
    grep -qx Enforcing "$run/adcinput-final-enforcing.txt" || rc=1
    if rg -q 'Sparrow|frida|group-observer' "$run/adcinput-processes-after.txt"; then rc=1; fi
    exit "$rc"
}
trap finalize EXIT
adb root > "$run/adcinput-adb-root.txt"
adb wait-for-device
sample_pid after_root
[ "$pid" = "$system_pid" ]
adb shell getenforce > "$run/adcinput-enforcing.txt"
grep -qx Enforcing "$run/adcinput-enforcing.txt"
adb shell pm list packages com.rigol.scope > "$run/adcinput-packages.txt"
[ ! -s "$run/adcinput-packages.txt" ]
adb shell ps > "$run/adcinput-processes-before.txt"
! rg -q 'Sparrow|frida|group-observer' "$run/adcinput-processes-before.txt"
native_path=$(yq -p toml -o yaml -r '.native.path' "$manifest")
native_dir=$(dirname "$repo/$native_path")
cp "$native_dir/"*.txt "$run/"
cp "$native_dir/group-observer" "$run/group-control.elf"
actual=$(shasum -a 256 "$run/group-control.elf"); actual=${actual%% *}
expected=$(yq -p toml -o yaml -r '.native.sha256' "$manifest")
[ "$actual" = "$expected" ]
cp "$repo/experiments/adc-transcript/reference.tsv" "$run/reference.tsv"
cp "$repo/experiments/calibration-static/loader-candidate.toml" "$run/calibration-loader-candidate.toml"
for kind in adc spu; do
    cp "$repo/out/$kind-transcript/derived-01/$kind-private.bin" "$run/$kind-private.bin"
    expected=$(yq -p toml -o yaml -r ".files[] | select(.path == \"$kind-private.bin\") | .sha256" "$repo/experiments/$kind-transcript/derivation.toml")
    actual=$(shasum -a 256 "$run/$kind-private.bin"); actual=${actual%% *}
    [ "$actual" = "$expected" ]
    adb push "$run/$kind-private.bin" "/data/local/tmp/$kind-private.bin" > "$run/$kind-private-push.txt" 2>&1
done
adb push "$run/group-control.elf" /data/local/tmp/group-observer > "$run/group-push.txt" 2>&1
adb shell chmod 755 /data/local/tmp/group-observer
arms=$(yq -p toml -o yaml -r '.arms[].arm' "$manifest")
[ -n "$arms" ]
for arm in $arms; do
    case "$arm" in ''|*[!0-9]*) exit 2;; esac
    capture_dir="/data/local/tmp/adc-input-captures-$arm"
    adb shell "test ! -e $capture_dir && mkdir $capture_dir" > "$run/adcinput-$arm-directory.txt" 2>&1
    rc=0
    adb shell "/data/local/tmp/group-observer control-adc-inputs $arm /data/local/tmp/adc-private.bin /data/local/tmp/spu-private.bin $capture_dir" \
        > "$run/adcinput-$arm.toml" 2>&1 || rc=$?
    printf 'exit_code = %s\n' "$rc" > "$run/adcinput-$arm-status.toml"
    for capture_file in loader-entry-lsb.bin loader-entry-adc.bin loader-terminal-lsb.bin loader-terminal-adc.bin loader-terminal-vertical.bin \
        adc-input-matrix.bin adc-input-setting.bin adc-input-drvparam.bin adc-input-series.bin adc-input-config.bin \
        adc-input-sample-entry.bin adc-input-shadow-low.bin adc-input-shadow-high.bin adc-input-global-inputs.bin adc-input-maps.txt; do
        pull_rc=0
        if adb shell "test -f $capture_dir/$capture_file"; then
            adb pull "$capture_dir/$capture_file" "$run/adcinput-$arm-$capture_file" \
                > "$run/adcinput-$arm-$capture_file-pull.txt" 2>&1 || pull_rc=$?
            printf '"%s" = %s\n' "$capture_file" "$pull_rc" >> "$run/adcinput-$arm-pulls.toml"
            [ "$pull_rc" = 0 ] || outcome=3
        fi
    done
    adb shell "ls -l $capture_dir" > "$run/adcinput-$arm-files.txt" 2>&1
    adb pull /data/local/tmp/group-observer "$run/adcinput-$arm.elf" > "$run/adcinput-$arm-binary-pull.txt" 2>&1
    cmp "$run/group-control.elf" "$run/adcinput-$arm.elf"
    sample_pid "after_arm_$arm"
    [ "$pid" = "$system_pid" ]
    if [ "$rc" != 78 ] || [ "$outcome" != 0 ]; then outcome=3; break; fi
    kotlin "$run/source/VerifyAdcInputCapture.main.kts" "$run" "$arm" \
        > "$run/adcinput-$arm-verification.toml" 2> "$run/adcinput-$arm-verification.stderr" || { outcome=3; break; }
done
exit "$outcome"
