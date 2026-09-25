#!/bin/sh
# Retrieve only pinned public reference files; never build or load the kernel driver.
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
manifest="$repo/experiments/xdma-boundary/reference.toml"
revision=$(yq -p toml -o yaml -r '.revision' "$manifest")
root=$(yq -p toml -o yaml -r '.local_root' "$manifest")
base="https://raw.githubusercontent.com/norbertkiszka/rigol-orangerigol-linux_4.4.179/$revision"
yq -p toml -o yaml -r '.files[] | [.path, .sha256, .git_blob] | @tsv' "$manifest" |
while IFS="$(printf '\t')" read -r relative expected blob; do
    destination="$repo/$root/$relative"
    if [ ! -e "$destination" ]; then
        mkdir -p "$(dirname "$destination")"
        curl -fsSL "$base/$relative" -o "$destination.part"
        actual=$(shasum -a 256 "$destination.part"); actual=${actual%% *}
        [ "$actual" = "$expected" ]
        [ "$(git hash-object "$destination.part")" = "$blob" ]
        mv "$destination.part" "$destination"
    fi
    actual=$(shasum -a 256 "$destination"); actual=${actual%% *}
    [ "$actual" = "$expected" ]
    [ "$(git hash-object "$destination")" = "$blob" ]
done
echo 'Pinned reference hashes verified'
