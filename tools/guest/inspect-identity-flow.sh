#!/bin/sh
# Read-only stock ELF dataflow capture; no guest execution.
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
run_id=${1:?Usage: inspect-identity-flow.sh RUN_ID}
case "$run_id" in ''|*[!a-zA-Z0-9_-]*) exit 2;; esac
llvm=${LLVM_BIN:?Set LLVM_BIN locally}
elf="$repo/local/reversing/firmware-extracted/stock-0.26/sparrow/base/lib/arm64-v8a/libscope-auklet.so"
run="$repo/out/xdma-identity-flow/$run_id"
[ ! -e "$run" ] || { echo 'Use a fresh run ID' >&2; exit 2; }
actual=$(shasum -a 256 "$elf"); actual=${actual%% *}
[ "$actual" = 4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e ]
mkdir -p "$run"
cp "$0" "$run/inspect-identity-flow.sh"
"$llvm/llvm-objdump" --version > "$run/llvm-version.txt"
shasum -a 256 "$llvm/llvm-objdump" "$llvm/llvm-readelf" "$llvm/llvm-nm" > "$run/tool-sha256.txt"
shasum -a 256 "$elf" > "$run/input-sha256.txt"
extract() { "$llvm/llvm-objdump" -d --demangle --start-address="$2" --stop-address="$3" "$elf" > "$run/$1.txt"; }
extract composition 0x2853ac 0x28546c
extract wrapper 0x2f18f8 0x2f1934
extract vendor-entry 0x42a284 0x42a2c4
extract getter 0x42a7dc 0x42a91c
extract transform 0x42a91c 0x42a9e0
"$llvm/llvm-readelf" -Wr "$elf" > "$run/relocations.txt"
"$llvm/llvm-nm" -D -S -C --defined-only "$elf" > "$run/dynamic-symbols.txt"
actual=$(shasum -a 256 "$elf"); actual=${actual%% *}
[ "$actual" = 4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e ]
for artifact in "$run"/*; do
    [ "$artifact" != "$run/evidence-sha256.txt" ] || continue
    shasum -a 256 "$artifact"
done > "$run/evidence-sha256.txt"
