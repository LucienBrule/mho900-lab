#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cc=${NATIVE_CC:?Set NATIVE_CC to pinned LLVM clang}
ld=${NATIVE_LD:?Set NATIVE_LD to pinned LLVM ld.lld}
out=${CACHED_IDENTITY_READER_DIR:?Set CACHED_IDENTITY_READER_DIR to a fresh output directory}
[ ! -e "$out" ] || { echo 'Output directory already exists' >&2; exit 1; }
hash() { shasum -a 256 "$1" | awk '{print $1}'; }
cc_hash=$(hash "$cc")
ld_hash=$(hash "$ld")
[ "$cc_hash" = 8daf964b5d524b4754d4300f370d9956a1de8f3815ce5828bb8fd8ad087b0b78 ]
[ "$ld_hash" = 1f80841d925f7b7d875d88e593e6e12dd496ab9227fc60f6ce9b07f73df6c81e ]
mkdir -p "$out"
cp "$repo/tools/guest/read-cached-identity.c" "$out/read-cached-identity.c"
cp "$repo/tools/guest/build-cached-identity-reader.sh" "$out/build-cached-identity-reader.sh"
cp "$repo/experiments/cached-identity-reader/inputs.toml" "$out/inputs.toml"
"$cc" --version > "$out/compiler.txt"
"$ld" --version > "$out/linker.txt"
"$cc" --target=aarch64-linux-gnu -O2 -ffreestanding -fno-builtin -fno-stack-protector \
 -nostdlib -static -fno-pic -Werror -Wall -Wextra --ld-path="$ld" \
 -Wl,-e,_start -Wl,--build-id=sha1 -o "$out/cached-identity-reader" "$out/read-cached-identity.c"
cat > "$out/build-manifest.toml" <<MANIFEST
schema_version = "mho900-lab.cached-identity-reader-build/1"
binary_sha256 = "$(hash "$out/cached-identity-reader")"
source_sha256 = "$(hash "$out/read-cached-identity.c")"
builder_sha256 = "$(hash "$out/build-cached-identity-reader.sh")"
inputs_sha256 = "$(hash "$out/inputs.toml")"
compiler_sha256 = "$cc_hash"
linker_sha256 = "$ld_hash"
target = "aarch64-linux-gnu"
static = true
libc = false
MANIFEST
chmod 700 "$out/cached-identity-reader"
