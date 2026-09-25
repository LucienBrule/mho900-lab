#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cc=${NATIVE_CC:?Set NATIVE_CC to LLVM clang}
ld=${NATIVE_LD:?Set NATIVE_LD to LLVM ld.lld}
profile=${EXECUTION_PROFILE:-strict}
case "$profile" in strict) cached=0; suffix=;; cached-enable) cached=1; suffix=-profile;; *) exit 2;; esac
out="$repo/local/guest-tools/execution-stop$suffix"
mkdir -p "$out"
"$cc" --version > "$out/compiler.txt"
"$ld" --version > "$out/linker.txt"
shasum -a 256 "$cc" "$ld" "$repo/tools/guest/execution-stop.c" "$repo/tools/guest/exclusive-control.c" > "$out/build-inputs.txt"
printf 'profile = %s\nCACHED_ENABLE_PROFILE = %s\n' "$profile" "$cached" > "$out/build-profile.txt"
"$cc" --target=aarch64-linux-gnu -DCACHED_ENABLE_PROFILE="$cached" -O2 -ffreestanding -fno-builtin -fno-stack-protector \
    -nostdlib -static -fno-pic -Werror -Wall -Wextra --ld-path="$ld" \
    -Wl,-e,_start -Wl,--build-id=sha1 -o "$out/execution-stop" "$repo/tools/guest/execution-stop.c"
shasum -a 256 "$out/execution-stop" > "$out/binary-sha256.txt"
