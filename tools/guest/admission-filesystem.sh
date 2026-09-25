#!/bin/sh
# One frozen filesystem construction in a disposable guest; stop on any failure.
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
capture() {
    key=$1; file=$2; shift 2
    rc=0
    adb "$@" > "$run/$file" 2>&1 || rc=$?
    printf '%s = %s\n' "$key" "$rc" >> "$run/fixture-command-status.toml"
    return "$rc"
}
source_root="$repo/local/reversing/firmware-extracted/stock-0.26"
if [ "${ADMISSION_MODE:-filesystem}" = adcsequencemodel ]; then
    source_root="$run/calibration-source"
else
    cp "$repo/experiments/calibration-static/loader-candidate.toml" "$run/calibration-loader-candidate.toml"
    cp "$repo/tools/research/InspectCalibrationAssets.main.kts" "$run/source/InspectCalibrationAssets.main.kts"
fi
kotlin "$run/source/InspectCalibrationAssets.main.kts" "$source_root" \
    "$run/calibration-asset-inspection.toml" > "$run/calibration-asset-check.toml" \
    2> "$run/calibration-asset-check.stderr"
for name in lsb vertical; do
    cp "$source_root/firmware/data/default/cal_$name.hex" "$run/calibration-$name-stock.bin"
    expected=$(yq -p toml -o yaml -r ".source_assets[] | select(.id == \"$name-default\") | .file_sha256" \
        "$run/calibration-loader-candidate.toml")
    actual=$(shasum -a 256 "$run/calibration-$name-stock.bin"); actual=${actual%% *}
    [ "$actual" = "$expected" ]
done
capture before_pid fixture-before-pid.txt shell pidof system_server
capture enforcing fixture-enforcing.txt shell getenforce
capture packages fixture-packages-before.txt shell pm list packages com.rigol.scope
capture processes fixture-processes-before.txt shell ps
capture adb_root fixture-adb-root.txt root
capture wait_device fixture-wait-device.txt wait-for-device
capture after_root_pid fixture-after-root-pid.txt shell pidof system_server
before=$(tr -d '\r\n' < "$run/fixture-before-pid.txt")
after=$(tr -d '\r\n' < "$run/fixture-after-root-pid.txt")
case "$before:$after" in *[!0-9:]*) exit 2;; esac
[ -n "$before" ] && [ "$before" = "$after" ]
printf 'before = %s\nafter_root = %s\n' "$before" "$after" > "$run/fixture-system-server.toml"
capture before_mounts fixture-before-mounts.txt shell cat /proc/mounts
capture before_mountinfo fixture-before-mountinfo.txt shell cat /proc/self/mountinfo
capture before_stat fixture-before-stat.txt shell "stat -c '%n %a %u %g' / /rigol"
capture before_labels fixture-before-labels.txt shell ls -ldZ / /rigol
capture before_empty fixture-before-empty.txt shell 'test -d /rigol && test ! -L /rigol && test -z "$(ls -A /rigol)"'
kotlin "$run/source/VerifyCalibrationFilesystem.main.kts" "$run" precondition \
    > "$run/fixture-precondition-verification.toml" 2> "$run/fixture-precondition-verification.stderr"
capture mount fixture-mount.txt shell 'mount -t tmpfs -o rw,nosuid,nodev,noexec,size=4m tmpfs /rigol'
capture mkdir fixture-mkdir.txt shell 'mkdir -p /rigol/data/default && chmod 755 /rigol /rigol/data /rigol/data/default'
for name in lsb vertical; do
    capture "push_$name" "calibration-$name-push.txt" push \
        "$run/calibration-$name-stock.bin" "/rigol/data/default/cal_$name.hex"
done
capture modes fixture-modes.txt shell 'chmod 644 /rigol/data/default/cal_lsb.hex /rigol/data/default/cal_vertical.hex'
capture absent_paths fixture-absent-paths.txt shell 'test ! -e /rigol/data/cal_lsb.hex && test ! -e /rigol/data/cal_vertical.hex && test ! -e /rigol/data/cal_adc.hex && test ! -e /rigol/data/default/cal_adc.hex'
capture after_mounts fixture-after-mounts.txt shell cat /proc/mounts
capture after_mountinfo fixture-after-mountinfo.txt shell cat /proc/self/mountinfo
capture after_stat fixture-after-stat.txt shell "stat -c '%n %a %u %g' /rigol /rigol/data /rigol/data/default /rigol/data/default/cal_lsb.hex /rigol/data/default/cal_vertical.hex"
capture after_labels fixture-after-labels.txt shell ls -ldZ /rigol /rigol/data /rigol/data/default \
    /rigol/data/default/cal_lsb.hex /rigol/data/default/cal_vertical.hex
for name in lsb vertical; do
    capture "pull_$name" "calibration-$name-pull.txt" pull \
        "/rigol/data/default/cal_$name.hex" "$run/calibration-$name-roundtrip.bin"
    cmp "$run/calibration-$name-stock.bin" "$run/calibration-$name-roundtrip.bin"
done
cat > "$run/fixture-result.toml" <<'END'
schema_version = "mho900-lab.calibration-filesystem-fixture/1"
result = "installed-and-roundtrip-matched"
stock_files = 2
absent_paths = 4
stock_application_access_observed = false
END
