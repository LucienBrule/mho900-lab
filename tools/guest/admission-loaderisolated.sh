#!/bin/sh
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
sample_pid() {
    pid=$(adb shell pidof system_server | tr -d '\r')
    case "$pid" in ''|*[!0-9]*) exit 2;; esac
    printf '%s = %s\n' "$1" "$pid" >> "$run/loader-system-server.toml"
}
sample_pid before
system_pid=$pid
adb shell getenforce > "$run/loader-enforcing.txt"
adb shell pm list packages com.rigol.scope > "$run/loader-packages.txt"
[ ! -s "$run/loader-packages.txt" ]
adb shell ps > "$run/loader-processes-before.txt"
! rg -q 'Sparrow|frida|group-observer' "$run/loader-processes-before.txt"
adb root > "$run/loader-adb-root.txt"
adb wait-for-device
sample_pid after_root
[ "$pid" = "$system_pid" ]

cp "$repo/experiments/calibration-loaders/isolated-inputs.toml" "$run/source/calibration-loader-inputs.toml"
cp "$repo/experiments/calibration-static/loader-candidate.toml" "$run/calibration-loader-candidate.toml"
cp "$repo/experiments/calibration-loaders/controls.toml" "$run/calibration-loader-controls.toml"
cp "$repo/experiments/calibration-loaders/native-protocol.md" "$run/calibration-loader-protocol.txt"
cp "$repo/experiments/calibration-loaders/run02-results.toml" "$run/legacy-control-results.toml"
cp "$repo/local/guest-tools/group-observer/"*.txt "$run/"
cp "$repo/local/guest-tools/group-observer/group-observer" "$run/group-control.elf"
actual=$(shasum -a 256 "$run/group-control.elf"); actual=${actual%% *}
[ "$actual" = 3c045ce88aeebf61da55e6026216995bbf562bf5ddd12560b9e4ce4296df40fa ]
cp "$repo/out/adc-transcript/derived-01/adc-private.bin" "$run/adc-private.bin"
cp "$repo/out/spu-transcript/derived-01/spu-private.bin" "$run/spu-private.bin"
cp "$repo/experiments/adc-transcript/reference.tsv" "$run/reference.tsv"
for kind in adc spu; do
    expected=$(yq -p toml -o yaml -r ".files[] | select(.path == \"$kind-private.bin\") | .sha256" \
        "$repo/experiments/$kind-transcript/derivation.toml")
    actual=$(shasum -a 256 "$run/$kind-private.bin"); actual=${actual%% *}
    [ "$actual" = "$expected" ]
    adb push "$run/$kind-private.bin" "/data/local/tmp/$kind-private.bin" > "$run/$kind-private-push.txt" 2>&1
done
adb push "$run/group-control.elf" /data/local/tmp/group-observer > "$run/group-push.txt" 2>&1
adb shell chmod 755 /data/local/tmp/group-observer

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
    adb pull /data/local/tmp/group-observer "$run/loader-$arm.elf" > "$run/loader-$arm-pull.txt" 2>&1
    cmp "$run/group-control.elf" "$run/loader-$arm.elf"
    sample_pid "after_arm_$arm"
    [ "$pid" = "$system_pid" ]
    if [ "$rc" != 78 ]; then outcome=3; break; fi
    kotlin "$run/source/VerifyCalibrationLoaders.main.kts" "$run" "$arm" \
        > "$run/loader-$arm-verification.toml" 2> "$run/loader-$arm-verification.stderr" || { outcome=3; break; }
done
adb shell getenforce >> "$run/loader-enforcing.txt"
adb shell pm list packages com.rigol.scope >> "$run/loader-packages.txt"
adb shell ps > "$run/loader-processes-after.txt"
[ "$(tr -d '\r' < "$run/loader-enforcing.txt" | awk 'NF { n++; if ($0 != "Enforcing") bad=1 } END { print n ":" (bad ? 1 : 0) }')" = "2:0" ]
[ ! -s "$run/loader-packages.txt" ]
! rg -q 'Sparrow|frida|group-observer' "$run/loader-processes-after.txt"
exit "$outcome"
