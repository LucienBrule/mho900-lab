#!/bin/sh
# Append project-relative artifact hashes to an authored TOML manifest.
set -eu
manifest=${1:?Usage: pin-artifacts.sh MANIFEST ARTIFACT...}
shift
[ -f "$manifest" ]
for artifact do
    case "$artifact" in /*|../*|*/../*|*\"*|*\\*) echo 'Use simple project-relative artifact paths' >&2; exit 2;; esac
    [ "$artifact" != "$manifest" ] || { echo 'Cannot hash manifest into itself' >&2; exit 2; }
    [ -f "$artifact" ]
    digest=$(shasum -a 256 "$artifact"); digest=${digest%% *}
    printf '\n[[artifacts]]\npath = "%s"\nsha256 = "%s"\n' "$artifact" "$digest" >> "$manifest"
done
