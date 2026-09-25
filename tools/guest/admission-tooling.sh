#!/bin/sh
# Sourced prerequisite phase, independently exercised before a new private suite.
runner_frida_prerequisites() {
    if [ "$mode" = adcsequencecontrol ]; then
        printf 'schema_version = "mho900-lab.frida-prerequisite/1"\nmode = "%s"\nrequired = false\nreason = "private native control suite"\n' "$mode" > "$run/frida-prerequisite.toml"
        return 0
    fi
    expected=$(yq -p toml -o yaml -r '.frida.server_sha256' "$admission_manifest")
    actual=$(shasum -a 256 "$repo/local/guest-tools/frida-16.7.19/server"); actual=${actual%% *}
    [ "$actual" = "$expected" ] || { echo 'Frida server mismatch' >&2; return 2; }
    [ "$("$repo/local/guest-tools/frida-16.7.19/venv/bin/frida" --version)" = 16.7.19 ] || return 2
    uv pip freeze --python "$repo/local/guest-tools/frida-16.7.19/venv/bin/python" > "$run/frida-packages.txt" || return 2
    printf 'schema_version = "mho900-lab.frida-prerequisite/1"\nmode = "%s"\nrequired = true\nserver_verified = true\ncli_version = "16.7.19"\n' "$mode" > "$run/frida-prerequisite.toml"
}
