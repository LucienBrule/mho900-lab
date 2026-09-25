#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cc=${NATIVE_CC:?Set NATIVE_CC to LLVM clang}
ld=${NATIVE_LD:?Set NATIVE_LD to LLVM ld.lld}
out="$repo/local/guest-tools/group-observer"
mkdir -p "$out"
"$cc" --version > "$out/compiler.txt"
"$ld" --version > "$out/linker.txt"
shasum -a 256 "$cc" "$ld" "$repo/tools/guest/group-observer.c" "$repo/tools/guest/thread-group.h" "$repo/tools/guest/native-probe.c" "$repo/tools/guest/native-post-store.h" > "$out/build-inputs.txt"
"$cc" --target=aarch64-linux-gnu -O2 -ffreestanding -fno-builtin -fno-stack-protector \
    -nostdlib -static -fno-pic -Werror -Wall -Wextra --ld-path="$ld" \
    -Wl,-e,_start -Wl,--build-id=sha1 -o "$out/group-observer" "$repo/tools/guest/group-observer.c"
shasum -a 256 "$out/group-observer" > "$out/binary-sha256.txt"
