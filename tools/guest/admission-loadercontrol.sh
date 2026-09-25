#!/bin/sh
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }

# Re-run the existing 0..75 controls against this executable first.
"$run/source/admission-tailcontrol.sh"
cp "$repo/experiments/calibration-loaders/inputs.toml" "$run/source/calibration-loader-inputs.toml"
cp "$repo/experiments/calibration-static/loader-candidate.toml" "$run/calibration-loader-candidate.toml"
cp "$repo/experiments/calibration-loaders/controls.toml" "$run/calibration-loader-controls.toml"
cp "$repo/experiments/calibration-loaders/native-protocol.md" "$run/calibration-loader-protocol.txt"

sample_pid() {
    pid=$(adb shell pidof system_server | tr -d '\r')
    case "$pid" in ''|*[!0-9]*) exit 2;; esac
    printf '%s = %s\n' "$1" "$pid" >> "$run/loader-system-server.toml"
}
sample_pid before
system_pid=$pid
adb shell getenforce > "$run/loader-enforcing.txt"
adb shell pm path com.rigol.scope > "$run/loader-packages.txt" 2>&1 || true
[ ! -s "$run/loader-packages.txt" ]
adb shell ps > "$run/loader-processes-before.txt"
! rg -q 'Sparrow|frida|group-observer' "$run/loader-processes-before.txt"

# File installation is itself bounded guest work; no stock app is installed here.
"$run/source/calibration-fixture.sh"
sample_pid after_fixture
[ "$pid" = "$system_pid" ]
arms=$(yq -p toml -o yaml -r '.arms[].arm' "$run/calibration-loader-controls.toml")
[ -n "$arms" ]
outcome=0
for arm in $arms; do
    case "$arm" in ''|*[!0-9]*) exit 2;; esac
    capture_dir="/data/local/tmp/loader-captures-$arm"
    adb shell "test ! -e $capture_dir && mkdir $capture_dir" > "$run/loader-$arm-directory.txt" 2>&1
    rc=0
    adb shell "/data/local/tmp/group-observer control-loaders $arm /data/local/tmp/adc-private.bin /data/local/tmp/spu-private.bin $capture_dir" \
        > "$run/loader-$arm.toml" 2>&1 || rc=$?
    printf 'exit_code = %s\n' "$rc" > "$run/loader-$arm-status.toml"
    for capture in entry-lsb entry-adc terminal-lsb terminal-adc terminal-vertical; do
        if adb shell "test -f $capture_dir/loader-$capture.bin"; then
            adb pull "$capture_dir/loader-$capture.bin" "$run/loader-$arm-$capture.bin" \
                > "$run/loader-$arm-$capture-pull.txt" 2>&1
        fi
    done
    adb shell "ls -l $capture_dir" > "$run/loader-$arm-files.txt" 2>&1
    adb pull /data/local/tmp/group-observer "$run/loader-$arm.elf" > "$run/loader-$arm-pull.txt"
    cmp "$run/group-control.elf" "$run/loader-$arm.elf"
    sample_pid "after_arm_$arm"
    [ "$pid" = "$system_pid" ]
    if [ "$rc" != 78 ]; then outcome=3; break; fi
    kotlin "$run/source/VerifyCalibrationLoaders.main.kts" "$run" "$arm" \
        > "$run/loader-$arm-verification.toml" 2> "$run/loader-$arm-verification.stderr" || { outcome=3; break; }
done

adb shell getenforce >> "$run/loader-enforcing.txt"
adb shell pm path com.rigol.scope >> "$run/loader-packages.txt" 2>&1 || true
adb shell ps > "$run/loader-processes-after.txt"
[ "$(tr -d '\r' < "$run/loader-enforcing.txt" | awk 'NF { n++; if ($0 != "Enforcing") bad=1 } END { print n ":" (bad ? 1 : 0) }')" = "2:0" ]
[ ! -s "$run/loader-packages.txt" ]
! rg -q 'Sparrow|frida|group-observer' "$run/loader-processes-after.txt"
exit "$outcome"
