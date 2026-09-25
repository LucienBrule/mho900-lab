#!/bin/sh
# A single frozen private sequence suite. Each arm has independent guest objects.
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
manifest="$run/source/adc-sequence-control-inputs.toml"
sample_pid() {
    pid=$(adb shell pidof system_server | tr -d '\r')
    case "$pid" in ''|*[!0-9]*) return 1;; esac
    printf '%s = %s\n' "$1" "$pid" >> "$run/adcseq-system-server.toml"
}
sample_pid before
system_pid=$pid
outcome=0
finalize() {
    rc=$?
    trap - EXIT
    adb shell getenforce > "$run/adcseq-final-enforcing.txt" 2>&1 || rc=1
    adb shell pm list packages com.rigol.scope > "$run/adcseq-final-packages.txt" 2>&1 || rc=1
    adb shell ps > "$run/adcseq-processes-after.txt" 2>&1 || rc=1
    sample_pid after || rc=1
    [ "$pid" = "$system_pid" ] || rc=1
    [ ! -s "$run/adcseq-final-packages.txt" ] || rc=1
    grep -qx Enforcing "$run/adcseq-final-enforcing.txt" || rc=1
    if rg -q 'Sparrow|frida|group-observer' "$run/adcseq-processes-after.txt"; then rc=1; fi
    exit "$rc"
}
trap finalize EXIT
adb root > "$run/adcseq-adb-root.txt"
adb wait-for-device
sample_pid after_root
[ "$pid" = "$system_pid" ]
adb shell getenforce > "$run/adcseq-enforcing.txt"
grep -qx Enforcing "$run/adcseq-enforcing.txt"
adb shell pm list packages com.rigol.scope > "$run/adcseq-packages.txt"
[ ! -s "$run/adcseq-packages.txt" ]
adb shell ps > "$run/adcseq-processes-before.txt"
! rg -q 'Sparrow|frida|group-observer' "$run/adcseq-processes-before.txt"
actual=$(shasum -a 256 "$run/group-control.elf"); actual=${actual%% *}
expected=$(yq -p toml -o yaml -r '.native.sha256' "$manifest")
[ "$actual" = "$expected" ]
for kind in adc spu; do
    expected=$(yq -p toml -o yaml -r ".artifacts[] | select(.run_path == \"$kind-private.bin\") | .sha256" "$manifest")
    actual=$(shasum -a 256 "$run/$kind-private.bin"); actual=${actual%% *}
    [ "$actual" = "$expected" ]
    adb push "$run/$kind-private.bin" "/data/local/tmp/$kind-private.bin" > "$run/$kind-private-push.txt" 2>&1
done
adb push "$run/group-control.elf" /data/local/tmp/group-observer > "$run/group-push.txt" 2>&1
adb shell chmod 755 /data/local/tmp/group-observer
arms=$(yq -p toml -o yaml -r '.arms[].arm' "$manifest")
[ "$(printf '%s\n' "$arms" | tr '\n' ' ')" = '101 102 103 104 105 106 107 108 109 110 111 112 ' ]
for arm in $arms; do
    case "$arm" in ''|*[!0-9]*) exit 2;; esac
    capture_dir="/data/local/tmp/adc-sequence-captures-$arm"
    adb shell "test ! -e $capture_dir && mkdir $capture_dir" > "$run/adcseq-$arm-directory.txt" 2>&1
    rc=0
    adb shell "/data/local/tmp/group-observer control-adc-sequence $arm /data/local/tmp/adc-private.bin /data/local/tmp/spu-private.bin $capture_dir" \
        > "$run/adcseq-$arm.toml" 2>&1 || rc=$?
    printf 'exit_code = %s\n' "$rc" > "$run/adcseq-$arm-status.toml"
    for capture_file in loader-entry-lsb.bin loader-entry-adc.bin loader-terminal-lsb.bin loader-terminal-adc.bin loader-terminal-vertical.bin \
        adc-input-matrix.bin adc-input-setting.bin adc-input-drvparam.bin adc-input-series.bin adc-input-config.bin \
        adc-input-sample-entry.bin adc-input-shadow-low.bin adc-input-shadow-high.bin adc-input-global-inputs.bin adc-input-maps.txt; do
        pull_rc=0
        if adb shell "test -f $capture_dir/$capture_file"; then
            adb pull "$capture_dir/$capture_file" "$run/adcseq-$arm-$capture_file" \
                > "$run/adcseq-$arm-$capture_file-pull.txt" 2>&1 || pull_rc=$?
            printf '"%s" = %s\n' "$capture_file" "$pull_rc" >> "$run/adcseq-$arm-pulls.toml"
            [ "$pull_rc" = 0 ] || outcome=3
        fi
    done
    adb shell "ls -l $capture_dir" > "$run/adcseq-$arm-files.txt" 2>&1
    adb pull /data/local/tmp/group-observer "$run/adcseq-$arm.elf" > "$run/adcseq-$arm-binary-pull.txt" 2>&1
    cmp "$run/group-control.elf" "$run/adcseq-$arm.elf"
    sample_pid "after_arm_$arm"
    [ "$pid" = "$system_pid" ]
    if [ "$rc" != 78 ] || [ "$outcome" != 0 ]; then outcome=3; break; fi
    kotlin "$run/source/VerifyAdcSequence.main.kts" "$run" "$arm" \
        > "$run/adcseq-$arm-verification.toml" 2> "$run/adcseq-$arm-verification.stderr" || { outcome=3; break; }
done
exit "$outcome"
