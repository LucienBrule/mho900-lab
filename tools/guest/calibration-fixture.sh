#!/bin/sh
# Install exact stock defaults only inside a fresh disposable guest.
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }

candidate="$run/calibration-loader-candidate.toml"
[ -f "$candidate" ]
source_root="$repo/local/reversing/firmware-extracted/stock-0.26"
cp "$repo/tools/research/InspectCalibrationAssets.main.kts" "$run/source/InspectCalibrationAssets.main.kts"
kotlin "$run/source/InspectCalibrationAssets.main.kts" "$source_root" \
    "$run/calibration-asset-inspection.toml" > "$run/calibration-asset-check.toml" \
    2> "$run/calibration-asset-check.stderr"
cp "$source_root/firmware/data/default/cal_lsb.hex" "$run/calibration-lsb-stock.bin"
cp "$source_root/firmware/data/default/cal_vertical.hex" "$run/calibration-vertical-stock.bin"
for name in lsb vertical; do
    expected=$(yq -p toml -o yaml -r ".source_assets[] | select(.id == \"$name-default\") | .file_sha256" "$candidate")
    actual=$(shasum -a 256 "$run/calibration-$name-stock.bin"); actual=${actual%% *}
    [ "$actual" = "$expected" ]
done

# A pre-existing tree is an unexpected environment, not something to overwrite.
adb shell 'test ! -e /rigol' > "$run/calibration-fixture-precondition.txt" 2>&1
adb shell getenforce > "$run/calibration-fixture-enforcing.txt"
adb shell pidof system_server > "$run/calibration-fixture-system-server-before.txt"
adb shell 'mount -o remount,rw / && mkdir -p /rigol/data/default && chmod 755 /rigol /rigol/data /rigol/data/default' \
    > "$run/calibration-fixture-setup.txt" 2>&1
for name in lsb vertical; do
    adb push "$run/calibration-$name-stock.bin" "/rigol/data/default/cal_$name.hex" \
        > "$run/calibration-$name-push.txt" 2>&1
done
adb shell 'chmod 644 /rigol/data/default/cal_lsb.hex /rigol/data/default/cal_vertical.hex' \
    > "$run/calibration-fixture-modes.txt" 2>&1
adb shell 'test ! -e /rigol/data/cal_lsb.hex && test ! -e /rigol/data/cal_vertical.hex && test ! -e /rigol/data/cal_adc.hex && test ! -e /rigol/data/default/cal_adc.hex' \
    > "$run/calibration-fixture-absent-paths.txt" 2>&1
adb shell 'ls -ldZ /rigol /rigol/data /rigol/data/default; ls -lZ /rigol/data/default; cat /proc/mounts' \
    > "$run/calibration-fixture-filesystem.txt" 2>&1
for name in lsb vertical; do
    adb pull "/rigol/data/default/cal_$name.hex" "$run/calibration-$name-roundtrip.bin" \
        > "$run/calibration-$name-pull.txt" 2>&1
    cmp "$run/calibration-$name-stock.bin" "$run/calibration-$name-roundtrip.bin"
done
adb shell getenforce >> "$run/calibration-fixture-enforcing.txt"
adb shell pidof system_server > "$run/calibration-fixture-system-server-after.txt"
cmp "$run/calibration-fixture-system-server-before.txt" "$run/calibration-fixture-system-server-after.txt"
[ "$(tr -d '\r' < "$run/calibration-fixture-enforcing.txt" | awk 'NF { n++; if ($0 != "Enforcing") bad=1 } END { print n ":" (bad ? 1 : 0) }')" = "2:0" ]
cat > "$run/calibration-fixture-result.toml" <<'EOF'
schema_version = "mho900-lab.calibration-filesystem-fixture/1"
result = "installed-and-roundtrip-matched"
stock_files = 2
absent_paths = 4
stock_application_access_observed = false
guest_enforcement_unchanged = true
system_server_pid_unchanged = true
EOF
