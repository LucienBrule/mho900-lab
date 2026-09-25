#!/bin/sh
# One stock whole-loader observation over the previously validated file fixture.
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
capture() {
    key=$1; file=$2; shift 2
    rc=0
    adb "$@" > "$run/$file" 2>&1 || rc=$?
    printf '%s = %s\n' "$key" "$rc" >> "$run/loader-command-status.toml"
    return "$rc"
}
stock_attempted=false
finalize() {
    outcome=$?
    trap - EXIT
    capture audit_logcat loader-audit-logcat.txt logcat -b all -d || outcome=1
    capture audit_dmesg loader-audit-dmesg.txt shell dmesg || true
    if [ "$stock_attempted" = true ]; then
        capture force_stop loader-force-stop.txt shell am force-stop com.rigol.scope || outcome=1
        # Record a clean package inventory even when admission stopped before installation.
        capture before_removal loader-before-removal-package.txt shell pm list packages com.rigol.scope || outcome=1
        if grep -qx 'package:com.rigol.scope' "$run/loader-before-removal-package.txt"; then
            capture uninstall loader-uninstall.txt uninstall com.rigol.scope || outcome=1
        fi
    fi
    capture final_package loader-final-package.txt shell pm list packages com.rigol.scope || outcome=1
    capture final_labels loader-final-labels.txt shell ls -ldZ /rigol /rigol/data /rigol/data/default \
        /rigol/data/default/cal_lsb.hex /rigol/data/default/cal_vertical.hex || outcome=1
    capture final_stat loader-final-stat.txt shell "stat -c '%n %a %u %g' /rigol /rigol/data /rigol/data/default /rigol/data/default/cal_lsb.hex /rigol/data/default/cal_vertical.hex" || outcome=1
    for name in lsb vertical; do
        capture "final_${name}_pull" "loader-final-$name-pull.txt" pull \
            "/rigol/data/default/cal_$name.hex" "$run/loader-final-$name.bin" || outcome=1
    done
    capture final_absent loader-final-absent.txt shell 'test ! -e /rigol/data/cal_lsb.hex && test ! -e /rigol/data/cal_vertical.hex && test ! -e /rigol/data/cal_adc.hex && test ! -e /rigol/data/default/cal_adc.hex' || outcome=1
    exit "$outcome"
}
trap finalize EXIT
fixture_rc=0
"$run/source/admission-filesystem.sh" || fixture_rc=$?
printf 'fixture_exit = %s\n' "$fixture_rc" >> "$run/loader-command-status.toml"
[ "$fixture_rc" = 0 ] || exit 1
kotlin "$run/source/VerifyCalibrationFilesystem.main.kts" "$run" fixture \
    > "$run/loader-fixture-verification.toml" 2> "$run/loader-fixture-verification.stderr"
manifest="$run/source/calibration-stock-inputs.toml"
[ "$(yq -p toml -o yaml -r '.fixture.profile' "$manifest")" = system-app-data ]
for name in lsb vertical; do
    capture "label_$name" "loader-label-$name.txt" shell chcon u:object_r:system_app_data_file:s0 \
        "/rigol/data/default/cal_$name.hex"
done
capture label_inventory loader-labelled-labels.txt shell ls -ldZ /rigol /rigol/data /rigol/data/default \
    /rigol/data/default/cal_lsb.hex /rigol/data/default/cal_vertical.hex
capture label_metadata loader-labelled-stat.txt shell "stat -c '%n %a %u %g' /rigol /rigol/data /rigol/data/default /rigol/data/default/cal_lsb.hex /rigol/data/default/cal_vertical.hex"
capture label_absent loader-labelled-absent.txt shell 'test ! -e /rigol/data/cal_lsb.hex && test ! -e /rigol/data/cal_vertical.hex && test ! -e /rigol/data/cal_adc.hex && test ! -e /rigol/data/default/cal_adc.hex'
cmp "$run/fixture-after-stat.txt" "$run/loader-labelled-stat.txt"
[ "$(grep -c 'u:object_r:tmpfs:s0' "$run/loader-labelled-labels.txt")" = 3 ]
[ "$(grep -c 'u:object_r:system_app_data_file:s0' "$run/loader-labelled-labels.txt")" = 2 ]
stock_attempted=true
stock_rc=0
"$run/source/admission-label.sh" || stock_rc=$?
printf 'stock_helper_exit = %s\n' "$stock_rc" >> "$run/loader-command-status.toml"
[ "$stock_rc" = 0 ]
# The shared admission helper preserves early failure evidence with a zero shell status.
# This profile requires actual stock execution and a completed native helper.
grep -qx 'install = "admitted"' "$run/probe-result.toml"
grep -qx 'launch = "attempted"' "$run/probe-result.toml"
grep -qx 'exit_code = 0' "$run/native-helper-status.toml"
