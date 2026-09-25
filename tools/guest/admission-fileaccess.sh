#!/bin/sh
# Observe one private system_app process reading the unchanged calibration fixture.
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
package=lab.mho900.calibration.access
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
capture() {
    key=$1; file=$2; shift 2
    rc=0
    adb "$@" > "$run/$file" 2>&1 || rc=$?
    printf '%s = %s\n' "$key" "$rc" >> "$run/access-command-status.toml"
    return "$rc"
}
installed=false
finalize() {
    outcome=$?
    trap - EXIT
    capture audit_logcat access-audit-logcat.txt logcat -b all -d || outcome=1
    capture audit_dmesg access-audit-dmesg.txt shell dmesg || true
    if [ "$installed" = true ]; then
        capture force_stop access-force-stop.txt shell am force-stop "$package" || outcome=1
        capture uninstall access-uninstall.txt uninstall "$package" || outcome=1
    fi
    capture final_packages access-final-packages.txt shell pm list packages "$package" || outcome=1
    capture final_processes access-final-processes.txt shell ps || outcome=1
    capture final_labels access-final-labels.txt shell ls -ldZ /rigol /rigol/data /rigol/data/default \
        /rigol/data/default/cal_lsb.hex /rigol/data/default/cal_vertical.hex || outcome=1
    for name in lsb vertical; do
        capture "final_${name}_pull" "access-final-$name-pull.txt" pull \
            "/rigol/data/default/cal_$name.hex" "$run/access-final-$name.bin" || outcome=1
    done
    exit "$outcome"
}
trap finalize EXIT
fixture_rc=0
"$run/source/admission-filesystem.sh" || fixture_rc=$?
printf 'fixture_exit = %s\n' "$fixture_rc" >> "$run/access-command-status.toml"
[ "$fixture_rc" = 0 ] || exit 1
kotlin "$run/source/VerifyCalibrationFilesystem.main.kts" "$run" fixture \
    > "$run/access-fixture-verification.toml" 2> "$run/access-fixture-verification.stderr"
manifest="$run/source/calibration-access-inputs.toml"
apk=$(yq -p toml -o yaml -r '.probe.apk_path' "$manifest")
expected=$(yq -p toml -o yaml -r '.probe.apk_sha256' "$manifest")
cp "$repo/$apk" "$run/access-control.apk"
actual=$(shasum -a 256 "$run/access-control.apk"); actual=${actual%% *}
[ "$actual" = "$expected" ]
cp "$repo/experiments/calibration-access/probe/"* "$run/source/"
"$sdk/build-tools/35.0.0/apksigner" verify --verbose --print-certs "$run/access-control.apk" \
    > "$run/access-signature.txt" 2> "$run/access-signature.stderr"
grep -q 'Signer #1 certificate SHA-256 digest: c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8' \
    "$run/access-signature.txt"
capture before_packages access-before-packages.txt shell pm list packages "$package"
[ ! -s "$run/access-before-packages.txt" ]
installed=true # Cleanup this unique package even if installation reporting fails.
capture install access-install.txt install "$run/access-control.apk"
grep -q '^Success' "$run/access-install.txt"
capture package_state access-package-state.txt shell dumpsys package "$package"
capture package_path access-package-path.txt shell pm path "$package"
installed_path=$(tr -d '\r' < "$run/access-package-path.txt" | sed -n 's/^package://p')
case "$installed_path" in /data/app/*/base.apk) ;; *) exit 2;; esac
case "$installed_path" in *[!a-zA-Z0-9_./=-]*) exit 2;; esac
capture installed_pull access-installed-pull.txt pull "$installed_path" "$run/access-installed.apk"
cmp "$run/access-control.apk" "$run/access-installed.apk"
capture launch access-launch.txt shell am start -W -n "$package/.ProbeActivity"
capture pid access-pid.txt shell pidof "$package"
pid=$(tr -d '\r\n' < "$run/access-pid.txt")
case "$pid" in ''|*[!0-9]*) exit 2;; esac
capture proc_status access-proc-status.txt shell cat "/proc/$pid/status"
capture proc_label access-proc-label.txt shell cat "/proc/$pid/attr/current"
deadline=$(( $(date +%s) + 20 ))
report="/data/data/$package/files/report.toml"
until adb shell "test -f $report"; do
    [ "$(date +%s)" -lt "$deadline" ] || exit 1
    sleep 1
done
capture report_pull access-report-pull.txt pull "$report" "$run/access-report.toml"
