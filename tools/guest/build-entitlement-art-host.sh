#!/bin/sh
# Java is used only for the Android app_process/ART platform entry point.
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
sdk=${ANDROID_SDK_ROOT:?Set ANDROID_SDK_ROOT locally}
out=${1:?Usage: build-entitlement-art-host.sh NEW_OUTPUT_DIRECTORY}
case "$out" in /*) ;; *) out="$repo/$out";; esac
case "$out" in "$repo/out/"*) ;; *) echo 'Use a fresh ignored out/ directory' >&2; exit 2;; esac
[ ! -e "$out" ]
java_bin=${JAVA_BIN:-$(command -v java)}
javac_bin=${JAVAC_BIN:-$(command -v javac)}
jdk=$(CDPATH= cd -- "$(dirname -- "$javac_bin")/.." && pwd -P)
tools="$sdk/build-tools/35.0.0"
android_jar="$sdk/platforms/android-35/android.jar"
[ -x "$java_bin" ] && [ -x "$javac_bin" ] && [ -f "$jdk/lib/modules" ]
[ -f "$tools/lib/d8.jar" ] && [ -f "$android_jar" ]
hash() { shasum -a 256 "$1" | awk '{print $1}'; }
umask 077
mkdir -p "$out/source" "$out/classes"
cp "$repo/tools/guest/art-host/EntitlementHost.java" "$out/source/"
cp "$0" "$out/source/"
"$java_bin" -version > "$out/java-version.txt" 2>&1
"$javac_bin" -version > "$out/javac-version.txt" 2>&1
"$java_bin" -cp "$tools/lib/d8.jar" com.android.tools.r8.D8 --version > "$out/d8-version.txt" 2>&1
"$javac_bin" --release 8 -d "$out/classes" "$out/source/EntitlementHost.java" > "$out/javac.log" 2>&1
"$java_bin" -cp "$tools/lib/d8.jar" com.android.tools.r8.D8 --min-api 25 --lib "$android_jar" \
    --output "$out/host.jar" "$out/classes/lab/mho900/guest/EntitlementHost.class" > "$out/d8.log" 2>&1
cat > "$out/host-build.toml" <<MANIFEST
schema_version = "mho900-lab.entitlement-art-host/1"
main_class = "lab.mho900.guest.EntitlementHost"
min_api = 25
java_release = 8
stock_class_loaded_by_host = false
host_sha256 = "$(hash "$out/host.jar")"
host_bytes = $(wc -c < "$out/host.jar" | tr -d ' ')
source_sha256 = "$(hash "$out/source/EntitlementHost.java")"
builder_sha256 = "$(hash "$out/source/build-entitlement-art-host.sh")"
java_sha256 = "$(hash "$java_bin")"
javac_sha256 = "$(hash "$javac_bin")"
jdk_modules_sha256 = "$(hash "$jdk/lib/modules")"
d8_launcher_sha256 = "$(hash "$tools/d8")"
d8_jar_sha256 = "$(hash "$tools/lib/d8.jar")"
android_jar_sha256 = "$(hash "$android_jar")"
MANIFEST
cat "$out/host-build.toml"
