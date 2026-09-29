#!/usr/bin/env python3
"""Copy exact accession inputs for a disposable native component experiment.

Python is used for its standard tar/ZIP readers, as in the accession inspector.
No archive path is extracted: selected contents are written to fixed destinations.
The output manifest is private because it fingerprints per-unit state.
"""
import argparse
import hashlib
import json
import pathlib
import shutil
import tarfile
import zipfile


def sha(path):
    with path.open("rb") as src:
        return hashlib.file_digest(src, "sha256").hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("apk", type=pathlib.Path)
    p.add_argument("rigol_tar", type=pathlib.Path)
    p.add_argument("ramdisk", type=pathlib.Path)
    p.add_argument("output", type=pathlib.Path)
    a = p.parse_args()
    assert not a.output.exists(), "Output must be fresh"
    assert sha(a.apk) == "6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b"
    assert sha(a.rigol_tar) == "f8c47fdfeb29ec043fb04ec91871b462d838652dfd1d2e8afa5c8d0044d4c33a"
    a.output.mkdir(parents=True, mode=0o700)
    (a.output / "lib").mkdir()
    (a.output / "rigol/data").mkdir(parents=True)
    with zipfile.ZipFile(a.apk) as z:
        for name in ("libc++_shared.so", "libfftw3f.so", "libscope-auklet.so"):
            member = "lib/arm64-v8a/" + name
            assert sum(i.filename == member for i in z.infolist()) == 1
            with z.open(member) as src, (a.output / "lib" / name).open("xb") as dst:
                shutil.copyfileobj(src, dst)
    with tarfile.open(a.rigol_tar, "r:") as t:
        for name in ("vendor.bin", "Key.data"):
            member = "rigol/data/" + name
            matches = [m for m in t if m.name == member]
            assert len(matches) == 1 and matches[0].isfile()
            assert 0 < matches[0].size <= 65536
            with t.extractfile(matches[0]) as src, (a.output / member).open("xb") as dst:
                shutil.copyfileobj(src, dst)
    assert sha(a.output / "lib/libscope-auklet.so") == (
        "4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e"
    )
    shutil.copyfile(a.ramdisk, a.output / "ramdisk.img")
    lines = [
        'schema_version = "mho900-lab.entitlement-fixture/1"',
        'scope = "stock native libraries and copied vendor/key files only"',
        'specimen_fram_present = false',
        'specimen_dna_known = false',
    ]
    for path in sorted(a.output.rglob("*")):
        if path.is_file():
            lines += ["", "[[files]]", "path = " + json.dumps(path.relative_to(a.output).as_posix()),
                      f"bytes = {path.stat().st_size}", 'sha256 = "' + sha(path) + '"']
    for label, path in (("apk", a.apk), ("rigol_archive", a.rigol_tar), ("ramdisk", a.ramdisk)):
        lines += ["", f"[inputs.{label}]", "path = " + json.dumps(str(path)),
                  'sha256 = "' + sha(path) + '"']
    (a.output / "fixture.toml").write_text("\n".join(lines) + "\n")
    print("Prepared private stock-native fixture; no guest or physical contact")


if __name__ == "__main__":
    main()
