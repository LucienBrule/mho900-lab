#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
sdk=${ANDROID_SDK_ROOT:?}
out=${1:?Usage: build-calibration-access.sh NEW_OUTPUT_DIRECTORY}
case "$out" in /*) ;; *) out="$repo/$out";; esac
[ ! -e "$out" ] || { echo 'Output directory already exists' >&2; exit 2; }

source_dir="$repo/experiments/calibration-access/probe"
key_dir="$repo/out/calibration-access/key-source"
tools="$sdk/build-tools/35.0.0"
android_jar="$sdk/platforms/android-35/android.jar"
kotlin_bin=${KOTLINC:-$(command -v kotlinc)}
kotlin_root=$(CDPATH= cd -- "$(dirname -- "$kotlin_bin")/.." && pwd -P)
stdlib="$kotlin_root/lib/kotlin-stdlib.jar"

hash() { shasum -a 256 "$1" | awk '{print $1}'; }
[ "$(hash "$key_dir/platform.x509.pem")" = 9837de028f460c35cc8d3fa45f14eecce30f6fbfe4b93d399aef1acb80c20d14 ]
[ "$(hash "$key_dir/platform.pk8")" = 1ad8ef556870edb70f69a9d3c112544c07de5162ba440d84d33f8bb0c5962875 ]
[ -f "$android_jar" ] && [ -f "$stdlib" ]

mkdir -p "$out/classes" "$out/dex"
"$tools/aapt" package -f -M "$source_dir/AndroidManifest.xml" -I "$android_jar" \
    -F "$out/probe-unsigned.apk"
"$kotlin_bin" "$source_dir/ProbeActivity.kt" -classpath "$android_jar" \
    -jvm-target 1.8 -d "$out/classes/probe.jar"
"$tools/d8" --min-api 25 --output "$out/dex" "$out/classes/probe.jar" "$stdlib"
(cd "$out/dex" && "$tools/aapt" add "$out/probe-unsigned.apk" classes.dex >/dev/null)
"$tools/apksigner" sign --key "$key_dir/platform.pk8" --cert "$key_dir/platform.x509.pem" \
    --out "$out/calibration-access.apk" "$out/probe-unsigned.apk"
"$tools/apksigner" verify --verbose --print-certs "$out/calibration-access.apk" \
    > "$out/apk-signature.txt"
grep -q 'Signer #1 certificate SHA-256 digest: c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8' \
    "$out/apk-signature.txt"
"$tools/aapt" dump xmltree "$out/calibration-access.apk" AndroidManifest.xml \
    > "$out/apk-manifest.txt"

cat > "$out/manifest.toml" <<EOF
schema_version = "mho900-lab.calibration-access-build/1"
apk = "calibration-access.apk"
apk_sha256 = "$(hash "$out/calibration-access.apk")"
apk_size = $(wc -c < "$out/calibration-access.apk" | tr -d ' ')
source_sha256 = "$(hash "$source_dir/ProbeActivity.kt")"
android_manifest_sha256 = "$(hash "$source_dir/AndroidManifest.xml")"
builder_sha256 = "$(hash "$repo/tools/guest/build-calibration-access.sh")"
platform_certificate_sha256 = "c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8"
platform_key_sha256 = "$(hash "$key_dir/platform.pk8")"
android_jar_sha256 = "$(hash "$android_jar")"
kotlinc_sha256 = "$(hash "$kotlin_bin")"
kotlin_stdlib_sha256 = "$(hash "$stdlib")"
aapt_sha256 = "$(hash "$tools/aapt")"
d8_sha256 = "$(hash "$tools/d8")"
apksigner_sha256 = "$(hash "$tools/apksigner")"
min_api = 25
jvm_target = "1.8"
package = "lab.mho900.calibration.access"
shared_user_id = "android.uid.system"
EOF
printf 'apk_sha256 = "%s"\n' "$(hash "$out/calibration-access.apk")"
