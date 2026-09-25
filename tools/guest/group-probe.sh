#!/bin/sh
# Stock two-read observation with converged thread-group supervision.
set -eu
run=${ADMISSION_RUN:?}
repo=${ADMISSION_REPO:?}
sdk=${ANDROID_SDK_ROOT:?}
adb() { gtimeout -k 2 30 "$sdk/platform-tools/adb" -P 5041 -s emulator-5580 "$@"; }
final_sample() {
    rc=$?
    trap - EXIT
    adb shell 'rm -f /dev/xdma0_bypass' > "$run/native-device-final-cleanup.txt" 2>&1 || true
    adb shell getenforce > "$run/native-final-enforcing.txt" 2>&1 || true
    adb shell pidof system_server > "$run/native-final-system-server.txt" 2>&1 || true
    exit "$rc"
}
trap final_sample EXIT

transcript=false
spu=false
remaining=false
tail=false
loaders=false
adcinputs=false
sequence=false
if [ "${ADMISSION_MODE:-groupmodel}" = adcsequencemodel ]; then sequence=true; adcinputs=true; fi
if [ "${ADMISSION_MODE:-groupmodel}" = adcinputmodel ]; then adcinputs=true; fi
if [ "${ADMISSION_MODE:-groupmodel}" = loadermodel ] || [ "$adcinputs" = true ]; then loaders=true; tail=true; remaining=true; spu=true; fi
if [ "${ADMISSION_MODE:-groupmodel}" = tailmodel ]; then tail=true; remaining=true; spu=true; fi
if [ "${ADMISSION_MODE:-groupmodel}" = remainingmodel ]; then remaining=true; spu=true; fi
[ "${ADMISSION_MODE:-groupmodel}" != spumodel ] || spu=true
if [ "${ADMISSION_MODE:-groupmodel}" = transcriptmodel ] || [ "$spu" = true ]; then
    transcript=true
    if [ "$sequence" != true ]; then
    canonical="$repo/out/adc-transcript/derived-01"
    cp "$canonical/adc-stock.bin" "$run/adc-stock.bin"
    cp "$repo/experiments/adc-transcript/reference.tsv" "$run/reference.tsv"
    cp "$repo/experiments/adc-transcript/derivation.toml" "$run/derivation.toml"
    fi
    actual=$(shasum -a 256 "$run/adc-stock.bin"); actual=${actual%% *}
    [ "$actual" = 42138210921f16b38a4627de3601cd9330bd413638bd96414e69a1a3d47592e7 ]
    actual=$(shasum -a 256 "$run/reference.tsv"); actual=${actual%% *}
    [ "$actual" = 6b9f7b8cdfba8d99fa720b2771cd741f285a05d5f9a77f0aa7173fbf5a2e39c9 ]
fi
if [ "$spu" = true ]; then
    if [ "$sequence" != true ]; then
    cp "$repo/out/spu-transcript/derived-01/spu-stock.bin" "$run/spu-stock.bin"
    cp "$repo/experiments/spu-transcript/derivation.toml" "$run/spu-derivation.toml"
    fi
    actual=$(shasum -a 256 "$run/spu-stock.bin"); actual=${actual%% *}
    [ "$actual" = 34ee0cb515117c91adc89ed065a66628e8f52283d0863a4b7f87b6cfb23be9a6 ]
fi
native_dir="$repo/local/guest-tools/group-observer"
if [ "$adcinputs" = true ] && [ "$sequence" != true ]; then
    native_path=$(yq -p toml -o yaml -r '.native.path' "$run/source/adc-input-capture-inputs.toml")
    native_dir=$(dirname "$repo/$native_path")
fi
if [ "$sequence" != true ]; then
    cp "$native_dir/"*.txt "$run/"
    cp "$native_dir/group-observer" "$run/group-control.elf"
fi
if [ "$transcript" = true ]; then
    actual=$(shasum -a 256 "$run/group-control.elf"); actual=${actual%% *}
    expected_binary=00cbc04e947881cecacfde64e9162e0f408f70cc15651a9d4185605ac3b13e7a
    [ "$spu" != true ] || expected_binary=ac86c83927a0bba752491c388e371d811d7bce9013007a51d2568837659311ae
    [ "$remaining" != true ] || expected_binary=8314d10b48c3cc69a4f51e28f61836dacd2f2b0c7a7831f2614a39fa3bf71e0d
    [ "$tail" != true ] || expected_binary=fd54590d662b0219459edd1e8dce8ad58738262bfcce346c9af2b4eadbc24182
    [ "$loaders" != true ] || expected_binary=3c045ce88aeebf61da55e6026216995bbf562bf5ddd12560b9e4ce4296df40fa
    if [ "$adcinputs" = true ]; then
        native_manifest="$run/source/adc-input-capture-inputs.toml"
        [ "$sequence" != true ] || native_manifest="$run/source/adc-sequence-stock-inputs.toml"
        expected_binary=$(yq -p toml -o yaml -r '.native.sha256' "$native_manifest")
    fi
    [ "$actual" = "$expected_binary" ]
fi
if [ "$remaining" = true ] && [ "$sequence" != true ]; then
    cp "$repo/experiments/remaining-init/stock-gate.toml" "$run/remaining-stock-gate.toml"
    cp "$repo/experiments/remaining-init/rearm-profile.toml" "$run/remaining-rearm-profile.toml"
    cp "$repo/experiments/remaining-init/grammar.toml" "$run/remaining-grammar.toml"
fi
if [ "$tail" = true ] && [ "$sequence" != true ]; then
    cp "$repo/experiments/init-tail/stock-gate.toml" "$run/tail-stock-gate.toml"
    cp "$repo/experiments/init-tail/candidate.toml" "$run/tail-candidate.toml"
    cp "$repo/experiments/init-tail/grammar.toml" "$run/tail-grammar.toml"
    cp "$repo/experiments/init-tail/controls-handoff.toml" "$run/tail-control-fixture.toml"
    cp "$repo/experiments/init-tail/handoff-profile.toml" "$run/tail-handoff-profile.toml"
fi
if [ "$sequence" != true ]; then cp "$repo/experiments/group-observer/fixture.toml" "$run/group-fixture.toml"; fi
adb push "$run/group-control.elf" /data/local/tmp/group-observer > "$run/group-push.txt"
adb shell chmod 755 /data/local/tmp/group-observer

pid=$(adb shell pidof com.rigol.scope | tr -d '\r')
case "$pid" in ''|*[!0-9]*) exit 2;; esac
printf 'pid = %s\n' "$pid" > "$run/native-app-pid.toml"
snapshot_rc=0
adb shell "cat /proc/$pid/cmdline; cat /proc/$pid/attr/current; cat /proc/$pid/maps" \
    > "$run/native-snapshot-composite.txt" 2> "$run/native-snapshot-composite-error.txt" || snapshot_rc=$?
printf 'exit_code = %s\n' "$snapshot_rc" > "$run/native-snapshot-composite-status.toml"
for part in cmdline label maps; do
    node=$part
    [ "$part" != label ] || node=attr/current
    snapshot_rc=0
    adb shell "cat /proc/$pid/$node" > "$run/native-snapshot-$part.txt" \
        2> "$run/native-snapshot-$part-error.txt" || snapshot_rc=$?
    printf 'exit_code = %s\n' "$snapshot_rc" > "$run/native-snapshot-$part-status.toml"
done
kotlin "$run/source/VerifySnapshot.main.kts" "$run" > "$run/native-snapshot-verification.toml"
cat "$run/native-snapshot-cmdline.txt" "$run/native-snapshot-label.txt" > "$run/native-before.txt"
printf '\n' >> "$run/native-before.txt"
cat "$run/native-snapshot-maps.txt" >> "$run/native-before.txt"

actual=$(unzip -p "$run/installed.apk" lib/arm64-v8a/libscope-auklet.so | shasum -a 256)
actual=${actual%% *}
[ "$actual" = 4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e ]
base=$(sed -n 's/^\([0-9a-f]*\)-.* r-xp 00f05000 .*com.rigol.scope.*\/base.apk$/\1/p' "$run/native-snapshot-maps.txt")
case "$base" in ''|*[!0-9a-f]*) exit 2;; esac

adb shell 'test ! -e /dev/xdma0_bypass && rm -f /data/local/tmp/native-events.toml /data/local/tmp/native-status.toml /data/local/tmp/native-pid' \
    > "$run/native-marker-reset.txt" 2>&1
command=stock
expected=0
input=/data/local/tmp/adc-stock.bin
if [ "$transcript" = true ]; then
    command=stock-transcript
    expected=78
    adb push "$run/adc-stock.bin" "$input" > "$run/adc-stock-push.txt"
fi
if [ "$spu" = true ]; then
    command=stock-spu
    adb push "$run/spu-stock.bin" /data/local/tmp/spu-stock.bin > "$run/spu-stock-push.txt"
fi
if [ "${ADMISSION_MODE:-groupmodel}" = nextmodel ] || [ "${ADMISSION_MODE:-groupmodel}" = writemodel ] || [ "${ADMISSION_MODE:-groupmodel}" = pairmodel ]; then
    command=stock-next
    expected=78
    cp "$repo/experiments/group-observer/continuation.toml" "$run/continuation-fixture.toml"
fi
if [ "${ADMISSION_MODE:-groupmodel}" = writemodel ] || [ "${ADMISSION_MODE:-groupmodel}" = pairmodel ]; then
    command=stock-write
    cp "$repo/experiments/group-observer/one-write.toml" "$run/write-fixture.toml"
fi
if [ "${ADMISSION_MODE:-groupmodel}" = pairmodel ]; then
    command=stock-pair-write
    cp "$repo/experiments/group-observer/two-writes.toml" "$run/pair-write-fixture.toml"
fi
[ "$remaining" != true ] || command=stock-remaining
[ "$tail" != true ] || command=stock-tail
[ "$loaders" != true ] || command=stock-loaders
[ "$adcinputs" != true ] || command=stock-adc-inputs
[ "$sequence" != true ] || command=stock-adc-sequence
command_args="$pid $base"
if [ "$transcript" = true ]; then command_args="$command_args $input"; fi
if [ "$spu" = true ]; then command_args="$command_args /data/local/tmp/spu-stock.bin"; fi
if [ "$loaders" = true ]; then
    adb shell 'test ! -e /data/local/tmp/stock-loader-captures && mkdir /data/local/tmp/stock-loader-captures' \
        > "$run/native-loader-directory.txt" 2>&1
    command_args="$command_args /data/local/tmp/stock-loader-captures"
fi
adb shell "/data/local/tmp/group-observer $command $command_args >/data/local/tmp/native-events.toml 2>&1 & observer=\$!; echo \$observer >/data/local/tmp/native-pid; wait \$observer; rc=\$?; echo exit_code = \$rc >/data/local/tmp/native-status.toml" \
    > "$run/native-command.txt" 2>&1 &
command_pid=$!
ready=false
for attempt in 1 2 3 4 5 6 7 8 9 10; do
    adb shell cat /data/local/tmp/native-events.toml > "$run/native-readiness.toml" 2>&1 || true
    if grep -q 'kind = "ready"' "$run/native-readiness.toml"; then ready=true; break; fi
    sleep 1
done
if [ "$ready" = true ]; then
    adb shell 'test ! -e /dev/xdma0_bypass && ln -s /dev/null /dev/xdma0_bypass; ls -lZ /dev/xdma0_bypass' \
        > "$run/native-device.txt" 2>&1
    for attempt in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
        if adb shell test -f /data/local/tmp/native-status.toml; then break; fi
        sleep 1
    done
fi
adb shell 'p=$(cat /data/local/tmp/native-pid 2>/dev/null || true); if [ -n "$p" ] && [ -r /proc/$p/cmdline ] && grep -q group-observer /proc/$p/cmdline; then kill -9 $p; fi; rm -f /dev/xdma0_bypass' \
    > "$run/native-cleanup.txt" 2>&1 || true
wait "$command_pid" || true
adb pull /data/local/tmp/native-events.toml "$run/native-events.toml" > "$run/native-events-pull.txt" 2>&1
adb pull /data/local/tmp/native-status.toml "$run/native-status.toml" > "$run/native-status-pull.txt" 2>&1
adb pull /data/local/tmp/group-observer "$run/group-executed.elf" > "$run/group-executed-pull.txt" 2>&1
if [ "$loaders" = true ]; then
    pulls_failed=false
    for capture in entry-lsb entry-adc terminal-lsb terminal-adc terminal-vertical; do
        pull_rc=0
        adb pull "/data/local/tmp/stock-loader-captures/loader-$capture.bin" \
            "$run/native-loader-$capture.bin" > "$run/native-loader-$capture-pull.txt" 2>&1 || pull_rc=$?
        printf '%s = %s\n' "$capture" "$pull_rc" >> "$run/native-loader-pulls.toml"
        [ "$pull_rc" = 0 ] || pulls_failed=true
    done
    [ "$pulls_failed" = false ] || exit 1
fi
if [ "$adcinputs" = true ]; then
    pulls_failed=false
    for capture in matrix setting drvparam series config sample-entry shadow-low shadow-high global-inputs maps; do
        suffix=bin
        [ "$capture" != maps ] || suffix=txt
        capture_file="adc-input-$capture.$suffix"
        pull_rc=0
        adb pull "/data/local/tmp/stock-loader-captures/$capture_file" "$run/$capture_file" \
            > "$run/$capture_file-pull.txt" 2>&1 || pull_rc=$?
        printf '%s = %s\n' "$capture" "$pull_rc" >> "$run/adc-input-pulls.toml"
        [ "$pull_rc" = 0 ] || pulls_failed=true
    done
    [ "$pulls_failed" = false ] || exit 1
fi
cmp "$run/group-control.elf" "$run/group-executed.elf"
adb shell getenforce > "$run/native-enforcing.txt"
grep -qx "exit_code = $expected" "$run/native-status.toml"
sleep 2
