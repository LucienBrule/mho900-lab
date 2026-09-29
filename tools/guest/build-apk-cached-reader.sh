#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cc=${NATIVE_CC:?Set NATIVE_CC to pinned clang}
ld=${NATIVE_LD:?Set NATIVE_LD to pinned ld.lld}
out=${APK_READER_BUILD_DIR:?Set APK_READER_BUILD_DIR to fresh directory}
[ ! -e "$out" ] || { echo 'Output exists' >&2; exit 1; }
hash() { shasum -a 256 "$1" | awk '{print $1}'; }
[ "$(hash "$cc")" = 8daf964b5d524b4754d4300f370d9956a1de8f3815ce5828bb8fd8ad087b0b78 ]
[ "$(hash "$ld")" = 1f80841d925f7b7d875d88e593e6e12dd496ab9227fc60f6ce9b07f73df6c81e ]
[ "$(hash "$repo/tools/guest/read-cached-identity.c")" = 1a49ad8d0577cf4b29fa69d686df587e995fa3d9eec7cb7178689613aa657438 ]
mkdir -p "$out"
cp "$repo/tools/guest/read-cached-identity.c" "$out/read-apk-cached-identity.c"
cp "$repo/tools/guest/apk-cached-identity.patch" "$out/reader.patch"
patch --batch --fuzz=0 "$out/read-apk-cached-identity.c" "$out/reader.patch"
cp "$repo/tools/guest/apk-cached-mapping-fixture.c" "$out/apk-cached-mapping-fixture.c"
cp "$0" "$out/build.sh"
for name in read-apk-cached-identity apk-cached-mapping-fixture; do
 "$cc" --target=aarch64-linux-gnu -O2 -ffreestanding -fno-builtin -fno-stack-protector \
  -nostdlib -static -fno-pic -Werror -Wall -Wextra --ld-path="$ld" \
  -Wl,-e,_start -Wl,--build-id=sha1 -o "$out/$name" "$out/$name.c"
done
{
 echo 'schema_version = 1'
 for name in read-apk-cached-identity read-apk-cached-identity.c apk-cached-mapping-fixture apk-cached-mapping-fixture.c reader.patch build.sh; do
  printf '\n[[files]]\npath = "%s"\nsha256 = "%s"\n' "$name" "$(hash "$out/$name")"
 done
} > "$out/build.toml"
