#!/bin/sh
# Sourced prerequisite phase, independently exercised before a new private suite.
runner_frida_prerequisites() {
    if [ "$mode" = adcsequencecontrol ]; then
        printf 'schema_version = "mho900-lab.frida-prerequisite/1"\nmode = "%s"\nrequired = false\nreason = "private native control suite"\n' "$mode" > "$run/frida-prerequisite.toml"
        return 0
    fi
    frida_home=${ADMISSION_FRIDA_HOME:-"$repo/local/guest-tools/frida-16.7.19"}
    if [ "$mode" = adcsequencemodel ]; then
        kotlin "$run/source/VerifyFridaEnvironment.main.kts" "$frida_home" "$run/source/frida-environment-files.toml" > "$run/frida-tooling-verification.toml" || return 2
        [ "$("$frida_home/venv/bin/python" --version)" = "Python 3.12.13" ] || return 2
        [ "$("$frida_home/venv/bin/python" -c 'from importlib.metadata import version; print(version("frida-tools"))')" = 13.7.1 ] || return 2
        uv pip check --python "$frida_home/venv/bin/python" > "$run/frida-package-check.txt" 2>&1 || return 2
    fi
    expected=$(yq -p toml -o yaml -r '.frida.server_sha256' "$admission_manifest")
    actual=$(shasum -a 256 "$frida_home/server"); actual=${actual%% *}
    [ "$actual" = "$expected" ] || { echo 'Frida server mismatch' >&2; return 2; }
    [ "$("$frida_home/venv/bin/frida" --version)" = 16.7.19 ] || return 2
    uv pip freeze --python "$frida_home/venv/bin/python" > "$run/frida-packages.txt" || return 2
    if [ "$mode" = adcsequencemodel ]; then
        yq -p toml -o yaml -r '.frida.packages[]' "$admission_manifest" | LC_ALL=C sort > "$run/frida-required-packages.txt"
        LC_ALL=C sort "$run/frida-packages.txt" > "$run/frida-observed-packages.txt"
        cmp "$run/frida-required-packages.txt" "$run/frida-observed-packages.txt" || return 2
    fi
    printf 'schema_version = "mho900-lab.frida-prerequisite/1"\nmode = "%s"\nrequired = true\nserver_verified = true\ncli_version = "16.7.19"\n' "$mode" > "$run/frida-prerequisite.toml"
}
