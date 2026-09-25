#!/bin/sh
# Sourced runtime collection/finalization; also exercised by host-only controls.
runner_capture() {
    capture_key=$1; capture_file=$2; shift 2
    phase=$capture_key
    capture_rc=0
    "$@" > "$run/$capture_file" 2>&1 || capture_rc=$?
    printf '%s_exit = %s\n' "$capture_key" "$capture_rc" >> "$run/runner-command-status.toml"
    return "$capture_rc"
}

runner_collect_boot() {
    runner_capture boot_getprop getprop.txt adb shell getprop
    runner_capture boot_kernel guest-kernel.txt adb shell uname -a
    runner_capture boot_surface surfaceflinger.txt adb shell dumpsys SurfaceFlinger || true
    phase=boot_screenshot
    screenshot_rc=0
    adb exec-out screencap -p > "$run/boot.png" 2> "$run/boot-screenshot-error.txt" || screenshot_rc=$?
    printf 'boot_screenshot_exit = %s\n' "$screenshot_rc" >> "$run/runner-command-status.toml"
    if [ "$screenshot_rc" = 0 ]; then graphics=screenshot_captured; else graphics=screenshot_failed; fi
    runner_capture boot_platform platform-apk-pull.txt adb pull /system/framework/framework-res.apk "$run/framework-res.apk" || true
    if [ -f "$run/framework-res.apk" ]; then
        runner_capture boot_signature platform-signature.txt "$timeout_bin" 20 \
            "$sdk/build-tools/35.0.0/apksigner" verify --print-certs "$run/framework-res.apk" || true
    fi
}

runner_health() {
    case "$mode" in loadercontrol|loaderisolated|filesystem|fileaccess|filelabel|loadermodel|adcinputcontrol|adcinputmodel|adcsequencecontrol)
        if [ "$boot" = completed ] && [ "$health_attempted" = false ]; then
            health_attempted=true
            health_rc=0
            "$run/source/admission-final-health.sh" || health_rc=$?
            printf 'final_health_helper_exit = %s\n' "$health_rc" >> "$run/final-health-status.toml"
            [ "$health_rc" = 0 ] || inspection=failed
        fi
        ;;
    esac
}

runner_index() {
    index_rc=0
    : > "$run/evidence-sha256.txt"
    for artifact in "$run"/*.txt "$run"/*.log "$run"/*.stderr "$run"/*.png "$run"/*.toml "$run"/*.policy \
        "$run"/*.bin "$run"/*.tsv "$run"/*.jar "$run"/*.odex "$run"/*.apk "$run"/*.xml "$run"/*.elf "$run"/seapp_contexts \
        "$run"/source/* "$run"/adc-parameter-static/*.toml "$run"/adc-candidate/*.toml "$run"/adc-candidate/*.tsv \
        "$run"/adc-sequence/*.toml "$run"/tombstones/* "$run"/fixture-ramdisk.img; do
        [ "$artifact" != "$run/evidence-sha256.txt" ] || continue
        [ -f "$artifact" ] || continue
        shasum -a 256 "$artifact" >> "$run/evidence-sha256.txt" || index_rc=1
    done
    return "$index_rc"
}

runner_write_result() {
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
runner_exit = $runner_exit
stopped_phase = "$stopped_phase"
final_health_attempted = $health_attempted
initial_index_exit = $initial_index_rc
EOF
}

runner_finalize() {
    runner_exit=$?
    trap - EXIT INT TERM
    # Attempt every final witness, even if transport or another capture fails.
    set +e
    stopped_phase=$phase
    [ "$runner_exit" = 0 ] || inspection=failed
    runner_health
    runner_capture final_logcat logcat-final.txt adb logcat -b all -d
    finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    if [ "$boot" != completed ] || [ "$inspection" != completed ]; then
        [ "$runner_exit" != 0 ] || runner_exit=1
    fi
    cleanup
    initial_index_rc=0
    runner_write_result
    result_rc=$?
    runner_index
    initial_index_rc=$?
    if [ "$result_rc" != 0 ] || [ "$initial_index_rc" != 0 ]; then
        runner_exit=1
        inspection=failed
        # Preserve a failed index separately, then include the corrected result
        # in a fresh best-effort index. No guest command is repeated.
        cp "$run/evidence-sha256.txt" "$run/evidence-index-incomplete.txt"
        runner_write_result
        runner_index
    fi
    cat "$run/result.toml"
    exit "$runner_exit"
}
