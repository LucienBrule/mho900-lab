#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
sdk=${ANDROID_SDK_ROOT:?}
controls="$repo/local/guest-inputs/admission-controls"
[ ! -e "$controls" ] || { echo 'Controls already exist; retain their provenance' >&2; exit 2; }
mkdir -p "$controls"
keytool -genkeypair -keystore "$controls/control.p12" -storepass research-control \
    -alias control -keyalg RSA -keysize 2048 -validity 30 -dname 'CN=mho900-lab research control' \
    > "$controls/key-generation.txt" 2>&1
for name in unrelated different-signer; do
    package=lab.mho900.admission.control
    [ "$name" != different-signer ] || package=com.rigol.scope
    mkdir "$controls/$name"
    cat > "$controls/$name/AndroidManifest.xml" <<EOF
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="$package" android:versionCode="1" android:sharedUserId="android.uid.system">
    <uses-sdk android:minSdkVersion="25" android:targetSdkVersion="25" />
    <application android:hasCode="false" android:label="Admission control" />
</manifest>
EOF
    "$sdk/build-tools/35.0.0/aapt" package -f -M "$controls/$name/AndroidManifest.xml" \
        -I "$sdk/platforms/android-35/android.jar" -F "$controls/$name-unsigned.apk"
    "$sdk/build-tools/35.0.0/apksigner" sign --ks "$controls/control.p12" \
        --ks-pass pass:research-control --out "$controls/$name.apk" "$controls/$name-unsigned.apk"
done
kotlinc -script "$repo/tools/guest/ChangedApkControl.main.kts" \
    "$repo/local/guest-inputs/Sparrow.apk" "$controls/changed-bytes.apk" > "$controls/change.toml"
for name in unrelated different-signer changed-bytes; do
    "$sdk/build-tools/35.0.0/apksigner" verify --verbose --print-certs "$controls/$name.apk" \
        > "$controls/$name-signature.txt"
done
shasum -a 256 "$controls"/*.apk > "$controls/sha256.txt"
