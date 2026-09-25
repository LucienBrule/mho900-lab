#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cc=${NATIVE_CC:?Set NATIVE_CC to LLVM clang}
ld=${NATIVE_LD:?Set NATIVE_LD to LLVM ld.lld}
out="$repo/local/guest-tools/execution-stop"
mkdir -p "$out"
"$cc" --version > "$out/compiler.txt"
"$ld" --version > "$out/linker.txt"
shasum -a 256 "$cc" "$ld" "$repo/tools/guest/execution-stop.c" "$repo/tools/guest/exclusive-control.c" > "$out/build-inputs.txt"
"$cc" --target=aarch64-linux-gnu -O2 -ffreestanding -fno-builtin -fno-stack-protector \
    -nostdlib -static -fno-pic -Werror -Wall -Wextra --ld-path="$ld" \
    -Wl,-e,_start -Wl,--build-id=sha1 -o "$out/execution-stop" "$repo/tools/guest/execution-stop.c"
shasum -a 256 "$out/execution-stop" > "$out/binary-sha256.txt"
