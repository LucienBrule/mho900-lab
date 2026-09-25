#!/bin/sh
# Stage an independently owned disposable image and leave a byte-identity receipt.
set -eu
source_image=${1:?Usage: stage-userdata.sh SOURCE NEW_TARGET RECEIPT MINIMUM_FREE_KIB}
target_image=${2:?}
receipt=${3:?}
minimum_free_kib=${4:?}
case "$minimum_free_kib" in ''|*[!0-9]*) exit 2;; esac
[ -f "$source_image" ]
[ ! -L "$source_image" ]
[ ! -e "$target_image" ]
[ ! -L "$target_image" ]
[ ! -e "$receipt" ]
[ ! -L "$receipt" ]
target_dir=$(dirname "$target_image")
[ -d "$target_dir" ]
free_kib() { df -Pk "$target_dir" | awk 'NR==2 {print $4}'; }
identity() {
    if [ "$(uname -s)" = Darwin ]; then /usr/bin/stat -f '%d:%i:%l' "$1";
    else stat -c '%d:%i:%h' "$1"; fi
}
hash_file() { shasum -a 256 "$1" | cut -d ' ' -f 1; }
before=$(free_kib)
[ "$before" -ge "$minimum_free_kib" ] || { echo 'Insufficient free space before userdata staging' >&2; exit 2; }
source_hash=$(hash_file "$source_image")
method=regular-copy
if [ "$(uname -s)" = Darwin ]; then
    # A clone has independent inode ownership; subsequent writes use COW.
    # Failure is explicit rather than silently consuming a full image copy.
    /bin/cp -c "$source_image" "$target_image"
    method=copy-on-write-clone
else
    cp "$source_image" "$target_image"
fi
[ -f "$target_image" ]
[ ! -L "$target_image" ]
source_identity=$(identity "$source_image")
target_identity=$(identity "$target_image")
[ "${target_identity##*:}" = 1 ]
[ "${source_identity%:*}" != "${target_identity%:*}" ]
target_hash=$(hash_file "$target_image")
[ "$source_hash" = "$target_hash" ]
[ "$(hash_file "$source_image")" = "$source_hash" ]
after=$(free_kib)
cat > "$receipt" <<RECEIPT
schema_version = "mho900-lab.userdata-staging/1"
method = "$method"
source_sha256 = "$source_hash"
staged_sha256 = "$target_hash"
source_identity = "$source_identity"
staged_identity = "$target_identity"
independent_inode = true
staged_link_count = 1
free_kib_before = $before
free_kib_after = $after
minimum_free_kib = $minimum_free_kib
RECEIPT
[ "$after" -ge "$minimum_free_kib" ] || { echo 'Insufficient free space after userdata staging' >&2; exit 2; }
