#!/bin/sh
# Exercise the production prerequisite function using disposable host fixtures.
set -eu
project=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
out=${1:?Usage: test-admission-tooling.sh NEW_OUTPUT}
[ ! -e "$out" ] || exit 2
mkdir -p "$out"
out=$(CDPATH= cd -- "$out" && pwd)
tooling="$project/tools/guest/admission-tooling.sh"
digest=$(shasum -a 256 "$tooling"); digest=${digest%% *}
printf 'schema_version = "mho900-lab.tooling-controls/1"\ntooling_sha256 = "%s"\nguest_launched = false\n' "$digest" > "$out/results.toml"
for case_id in private-absent retained-positive changed-server missing-cli wrong-version; do
    case_dir="$out/$case_id"
    repo="$case_dir/repo"; run="$case_dir/run"; admission_manifest="$case_dir/inputs.toml"
    mkdir -p "$repo" "$run" "$case_dir/bin"
    mode=adcsequencecontrol; expected_rc=0
    if [ "$case_id" != private-absent ]; then
        mode=inspect
        fixture="$repo/local/guest-tools/frida-16.7.19"
        mkdir -p "$fixture/venv/bin"
        printf 'synthetic server\n' > "$fixture/server"
        server_digest=$(shasum -a 256 "$fixture/server"); server_digest=${server_digest%% *}
        printf '[frida]\nserver_sha256 = "%s"\n' "$server_digest" > "$admission_manifest"
        printf '#!/bin/sh\nprintf "16.7.19\\n"\n' > "$fixture/venv/bin/frida"
        chmod +x "$fixture/venv/bin/frida"
        printf '#!/bin/sh\nprintf "synthetic-package==1\\n"\n' > "$case_dir/bin/uv"
        chmod +x "$case_dir/bin/uv"
        case "$case_id" in
            changed-server) printf 'changed\n' >> "$fixture/server"; expected_rc=2;;
            missing-cli) rm "$fixture/venv/bin/frida"; expected_rc=2;;
            wrong-version) printf '#!/bin/sh\nprintf "0.0.0\\n"\n' > "$fixture/venv/bin/frida"; expected_rc=2;;
        esac
    fi
    set +e
    ( PATH="$case_dir/bin:$PATH"; export PATH; . "$tooling"; runner_frida_prerequisites ) > "$case_dir/stdout.txt" 2> "$case_dir/stderr.txt"
    rc=$?
    set -e
    [ "$rc" = "$expected_rc" ] || { echo "Unexpected $case_id exit $rc" >&2; exit 1; }
    if [ "$rc" = 0 ]; then
        [ -f "$run/frida-prerequisite.toml" ]
        required=$(yq -p toml -o yaml -r '.required' "$run/frida-prerequisite.toml")
        if [ "$case_id" = private-absent ]; then
            [ "$required" = false ]; [ ! -e "$run/frida-packages.txt" ]; [ ! -e "$repo/local" ]
        else
            [ "$required" = true ]; [ -s "$run/frida-packages.txt" ]
        fi
    else
        [ ! -e "$run/frida-prerequisite.toml" ]
    fi
    printf '\n[[cases]]\nname = "%s"\nexit_code = %s\nexpected_outcome = true\n' "$case_id" "$rc" >> "$out/results.toml"
done
printf 'Prerequisite controls: two positives and three negatives matched\n'
