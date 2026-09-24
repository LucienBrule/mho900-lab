#!/bin/sh
# Acquire the pinned instrumentation runtime locally; no global installation.
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
manifest="$repo/experiments/guest-admission/inputs.toml"
destination="$repo/local/guest-tools/frida-16.7.19"
value() { yq -p toml -r "$1" "$manifest"; }
check() {
    actual=$(shasum -a 256 "$1"); actual=${actual%% *}
    [ "$actual" = "$2" ] || { echo 'Instrumentation hash mismatch' >&2; exit 2; }
}
mkdir -p "$destination"
if [ ! -f "$destination/server.xz" ]; then
    curl -fL --max-time 120 "$(value .frida.server_url)" -o "$destination/server.xz.part"
    check "$destination/server.xz.part" "$(value .frida.archive_sha256)"
    mv "$destination/server.xz.part" "$destination/server.xz"
fi
check "$destination/server.xz" "$(value .frida.archive_sha256)"
if [ ! -f "$destination/server" ]; then xz -dk "$destination/server.xz"; fi
check "$destination/server" "$(value .frida.server_sha256)"
if [ ! -d "$destination/venv" ]; then uv venv --python "$(value .frida.python_version)" "$destination/venv"; fi
value '.frida.packages[]' > "$destination/requirements.txt"
uv pip install --python "$destination/venv/bin/python" -r "$destination/requirements.txt"
uv pip check --python "$destination/venv/bin/python"
"$destination/venv/bin/frida" --version
