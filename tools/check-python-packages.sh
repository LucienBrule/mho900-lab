#!/bin/sh
# Build and test only installed wheels; keep logs in a new caller-selected directory.
set -eu
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 NEW_EVIDENCE_DIRECTORY" >&2
    exit 2
fi
cd "$(dirname "$0")/.."
workspace=$(pwd -P)
mkdir "$1"
evidence=$(cd "$1" && pwd -P)
cp uv.lock "$evidence/uv.lock"
cp pyproject.toml "$evidence/workspace.toml"
cp packages/mho-lab-cli/tests/installed_smoke.py "$evidence/installed_smoke.py"
uv --version > "$evidence/uv-version.txt"
python_version=$(cat .python-version)
python_executable=$(uv python find "$python_version")
"$python_executable" --version > "$evidence/python-version.txt" 2>&1
scratch=$(mktemp -d "${TMPDIR:-/tmp}/mho-wheel-check.XXXXXXXX")
scratch=$(cd "$scratch" && pwd -P)
case "$scratch/" in
    "$workspace/"*) echo "Isolated environment must be outside the checkout." >&2; exit 2 ;;
esac
cleanup() {
    code=$?
    trap - EXIT HUP INT TERM
    if [ "$code" -eq 0 ]; then
        printf 'result = "accepted"\nexit_code = 0\n' > "$evidence/orchestrator.toml"
        rm -rf -- "$scratch"
    else
        printf 'result = "failed"\nexit_code = %s\n' "$code" > "$evidence/orchestrator.toml"
        printf '%s\n' "$scratch" > "$evidence/retained-environment.txt"
        echo "Packaging check failed; logs and retained environment recorded in $evidence" >&2
    fi
    exit "$code"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
uv export --locked --all-packages --no-dev --no-emit-workspace --no-annotate --no-header \
    --output-file "$evidence/dependencies.txt" > "$evidence/export.log" 2>&1
uv export --locked --only-group build --no-emit-workspace --no-annotate --no-header \
    --output-file "$evidence/build-constraints.txt" > "$evidence/build-export.log" 2>&1
uv --verbose build --all-packages --python "$python_executable" \
    --build-constraints "$evidence/build-constraints.txt" \
    --out-dir "$evidence/distributions" > "$evidence/build.log" 2>&1
for source_archive in "$evidence"/distributions/*.tar.gz; do
    uv --verbose build --wheel "$source_archive" --python "$python_executable" \
        --build-constraints "$evidence/build-constraints.txt" \
        --out-dir "$evidence/wheels" >> "$evidence/sdist-rebuild.log" 2>&1
done
cmp uv.lock "$evidence/uv.lock"
cmp pyproject.toml "$evidence/workspace.toml"
uv venv --python "$python_executable" "$scratch/environment" > "$evidence/venv.log" 2>&1
installed_python="$scratch/environment/bin/python"
uv pip install --python "$installed_python" --require-hashes \
    --requirement "$evidence/dependencies.txt" > "$evidence/dependencies-install.log" 2>&1
uv pip install --python "$installed_python" --no-deps "$evidence"/wheels/*.whl \
    > "$evidence/wheels-install.log" 2>&1
uv pip check --python "$installed_python" > "$evidence/dependencies-check.log" 2>&1
cp "$evidence/installed_smoke.py" "$scratch/installed_smoke.py"
mkdir "$scratch/work"
cd "$scratch/work"
MHO_PACKAGE_CHECKOUT="$workspace" MHO_PACKAGE_EVIDENCE="$evidence" \
    "$installed_python" -I "$scratch/installed_smoke.py" \
    > "$evidence/smoke.log" 2>&1
printf 'Installed-wheel checks passed; evidence: %s\n' "$evidence"
