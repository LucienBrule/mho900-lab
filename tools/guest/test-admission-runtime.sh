#!/bin/sh
# Host-only controls for the sourced admission runtime. No guest is launched.
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
out=${1:?Usage: test-admission-runtime.sh OUTPUT_DIRECTORY [loadermodel|adcinputcontrol|adcinputmodel|adcsequencecontrol]}
control_mode=${2:-loadermodel}
case "$control_mode" in loadermodel|adcinputcontrol|adcinputmodel|adcsequencecontrol) ;; *) exit 2;; esac
[ ! -e "$out" ] || { echo "Output exists: $out" >&2; exit 2; }
mkdir -p "$out/cases"
runtime="$repo/tools/guest/admission-runtime.sh"
runtime_hash=$(shasum -a 256 "$runtime"); runtime_hash=${runtime_hash%% *}

run_case() {
    id=$1 expected_rc=$2 expected_phase=$3 expected_helper=$4 expected_health=$5
    case_dir="$out/cases/$id"
    run="$case_dir/run"
    mkdir -p "$run/source"
    cat > "$run/source/admission-final-health.sh" <<'EOF'
#!/bin/sh
count=0
[ ! -f "$ADMISSION_RUN/health-count.txt" ] || count=$(cat "$ADMISSION_RUN/health-count.txt")
count=$((count + 1))
printf '%s\n' "$count" > "$ADMISSION_RUN/health-count.txt"
[ "${CONTROL_CASE:-}" != final-health-failure ]
EOF
    chmod +x "$run/source/admission-final-health.sh"
    set +e
    CONTROL_MODE=$control_mode CONTROL_CASE=$id CONTROL_RUN=$run CONTROL_RUNTIME=$runtime sh <<'EOF' > "$case_dir/stdout.txt" 2> "$case_dir/stderr.txt"
set -eu
run=$CONTROL_RUN
run_id="runtime-$CONTROL_CASE"
mode=$CONTROL_MODE
sdk=/mock-sdk
timeout_bin=/mock-timeout
started=2026-09-25T00:00:00Z
boot=completed
install=not_reached
launch=not_reached
graphics=not_reached
emulator_exit=not_observed
inspection=not_reached
health_attempted=false
phase=boot_collection
emulator_pid=
logcat_pid=
export ADMISSION_RUN=$run CONTROL_CASE
cleanup() {
    count=0
    [ ! -f "$run/cleanup-count.txt" ] || count=$(cat "$run/cleanup-count.txt")
    printf '%s\n' "$((count + 1))" > "$run/cleanup-count.txt"
}
adb() {
    command=$*
    case "$command" in
        "shell getprop")
            printf '[sys.boot_completed]: [1]\n'
            [ "$CONTROL_CASE" != getprop-output-then-255 ] || return 255
            ;;
        "shell uname -a")
            printf 'Linux mock 4.4 arm64\n'
            [ "$CONTROL_CASE" != uname-failure ] || return 9
            ;;
        "shell dumpsys SurfaceFlinger")
            printf 'mock surface\n'
            [ "$CONTROL_CASE" != optional-collection-failure ] || return 7
            ;;
        "exec-out screencap -p")
            printf 'PNG'
            [ "$CONTROL_CASE" != optional-collection-failure ] || return 8
            ;;
        "pull /system/framework/framework-res.apk "*)
            [ "$CONTROL_CASE" != optional-collection-failure ] || return 6
            printf 'mock pull\n'
            ;;
        "logcat -b all -d") printf 'mock final logcat\n' ;;
        *) printf 'unexpected adb call: %s\n' "$command" >&2; return 99 ;;
    esac
}
shasum() {
    if [ "$CONTROL_CASE" = index-hash-failure ] && [ "$*" = "-a 256 $run/result.toml" ] && [ ! -e "$run/index-failure-injected.txt" ]; then
        printf 'first result.toml hash rejected\n' > "$run/index-failure-injected.txt"
        return 23
    fi
    command shasum "$@"
}
. "$CONTROL_RUNTIME"
trap runner_finalize EXIT
trap 'exit 130' INT TERM
if [ "$CONTROL_CASE" = early-runtime-abort ]; then
    boot=not_started
    phase=runtime_abort
    exit 17
fi
runner_collect_boot
phase=admission_helper
inspection=completed
printf 'called\n' > "$run/admission-helper.txt"
runner_health
phase=finished
[ "$boot" = completed ] && [ "$inspection" = completed ]
EOF
    rc=$?
    set -e
    [ "$rc" = "$expected_rc" ]
    result="$run/result.toml"
    [ -f "$result" ]
    grep -qx "runner_exit = $expected_rc" "$result"
    grep -qx "stopped_phase = \"$expected_phase\"" "$result"
    grep -qx "final_health_attempted = $([ "$expected_health" = 1 ] && printf true || printf false)" "$result"
    [ "$(cat "$run/cleanup-count.txt")" = 1 ]
    actual_health=0
    [ ! -f "$run/health-count.txt" ] || actual_health=$(cat "$run/health-count.txt")
    [ "$actual_health" = "$expected_health" ]
    if [ "$expected_helper" = 1 ]; then [ -f "$run/admission-helper.txt" ]; else [ ! -e "$run/admission-helper.txt" ]; fi
    status="$run/runner-command-status.toml"
    [ -f "$status" ]
    case "$id" in
        getprop-output-then-255)
            grep -qx 'boot_getprop_exit = 255' "$status"
            [ ! -e "$run/guest-kernel.txt" ]
            ;;
        uname-failure)
            grep -qx 'boot_getprop_exit = 0' "$status"
            grep -qx 'boot_kernel_exit = 9' "$status"
            ;;
        optional-collection-failure)
            grep -qx 'boot_surface_exit = 7' "$status"
            grep -qx 'boot_screenshot_exit = 8' "$status"
            grep -qx 'boot_platform_exit = 6' "$status"
            ;;
        index-hash-failure)
            grep -qx 'runner_exit = 1' "$result"
            grep -qx 'inspection = "failed"' "$result"
            grep -qx 'initial_index_exit = 1' "$result"
            [ -s "$run/evidence-index-incomplete.txt" ]
            ! grep -F "  $run/result.toml" "$run/evidence-index-incomplete.txt" >/dev/null
            [ -s "$run/index-failure-injected.txt" ]
            ;;
    esac
    index="$run/evidence-sha256.txt"
    [ -f "$index" ]
    [ "$(cut -c67- "$index" | sort | uniq -d | wc -l | tr -d ' ')" = 0 ]
    while IFS= read -r row; do
        expected=${row%%  *}; file=${row#*  }
        [ -f "$file" ]
        actual=$(shasum -a 256 "$file"); actual=${actual%% *}
        [ "$actual" = "$expected" ]
    done < "$index"
    for required in result.toml runner-command-status.toml cleanup-count.txt stdout.txt; do
        case "$required" in stdout.txt) file="$case_dir/$required";; *) file="$run/$required";; esac
        if [ "$required" != stdout.txt ]; then grep -F "  $file" "$index" >/dev/null; fi
    done
    printf '%s %s %s\n' "$id" "$rc" "$expected_phase" >> "$out/case-results.txt"
}

run_case success 0 finished 1 1
run_case getprop-output-then-255 255 boot_getprop 0 1
run_case uname-failure 9 boot_kernel 0 1
run_case final-health-failure 1 finished 1 1
run_case optional-collection-failure 0 finished 1 1
run_case early-runtime-abort 17 runtime_abort 0 0
run_case index-hash-failure 1 finished 1 1

cat > "$out/results.toml" <<EOF
schema_version = "mho900-lab.admission-runtime-controls/1"
result = "accepted"
kind = "host-only-mocked-runtime"
mode = "$control_mode"
runtime_sha256 = "$runtime_hash"
cases = 7
guest_launched = false
writable_links_used = false
all_expected_exits = true
all_stopped_phases = true
all_indexes_verified = true
cleanup_exactly_once = true
final_health_attempt_rules_verified = true
mandatory_failure_skips_admission = true
index_failure_preserves_partial_and_corrects_result = true
EOF
printf 'runtime_controls = "accepted"\n'
