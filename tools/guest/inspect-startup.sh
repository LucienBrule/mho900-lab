#!/bin/sh
# External decompiler/disassembler orchestration; derived proprietary output stays local.
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
run_id=${1:?Usage: inspect-startup.sh RUN_ID}
case "$run_id" in ''|*[!a-zA-Z0-9_-]*) exit 2;; esac
llvm=${LLVM_BIN:?Set LLVM_BIN to the LLVM tool directory}
jadx=${JADX_BIN:-jadx}
apk="$repo/local/guest-inputs/Sparrow.apk"
library="$repo/local/reversing/firmware-extracted/stock-0.26/sparrow/base/lib/arm64-v8a/libscope-auklet.so"
out="$repo/out/guest-startup/$run_id"
[ ! -e "$out" ] || { echo 'Choose a fresh output ID' >&2; exit 2; }
actual=$(shasum -a 256 "$apk"); actual=${actual%% *}
[ "$actual" = 6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b ]
actual=$(shasum -a 256 "$library"); actual=${actual%% *}
[ "$actual" = 4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e ]
packaged=$(unzip -p "$apk" lib/arm64-v8a/libscope-auklet.so | shasum -a 256); packaged=${packaged%% *}
[ "$actual" = "$packaged" ]
mkdir -p "$out"
cp "$0" "$out/inspect-startup.sh"
shasum -a 256 "$apk" "$library" > "$out/input-sha256.txt"
"$jadx" --version > "$out/jadx-version.txt"
"$llvm/llvm-objdump" --version > "$out/llvm-version.txt"
shasum -a 256 "$llvm/llvm-objdump" "$llvm/llvm-readelf" > "$out/llvm-sha256.txt"
for class in SplashActivity cil.API; do
    "$jadx" -r --single-class "com.rigol.scope.$class" --single-class-output "$out/$class.java" \
        "$apk" > "$out/jadx-$class.log" 2>&1
done
"$llvm/llvm-readelf" -l "$library" > "$out/program-headers.txt"
"$llvm/llvm-readelf" -Ws "$library" > "$out/auklet-symbols.txt"
"$llvm/llvm-objdump" -d --demangle --disassemble-symbols=JNI_StartBusiness,Dev_PCIeInit \
    "$library" > "$out/native-startup.txt"
"$llvm/llvm-objdump" -d --demangle --start-address=0x2390cc --stop-address=0x2392f4 \
    "$library" > "$out/factory-init.txt"
# The containing PT_LOAD has equal file offset and virtual address; header is captured above.
dd if="$library" bs=1 skip=$((0x993543)) count=18 2>/dev/null | od -An -tx1c > "$out/pcie-device-string.txt"
for artifact in "$out"/*; do
    [ "$artifact" != "$out/checksums.txt" ] || continue
    shasum -a 256 "$artifact"
done > "$out/checksums.txt"
