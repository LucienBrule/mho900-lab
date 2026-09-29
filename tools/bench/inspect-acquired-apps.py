#!/usr/bin/env python3
"""Hash acquired APKs and Auklet members without extracting arbitrary archive paths.

Output is private evidence. Originals are read-only inputs. No device access.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inspect(archives, output):
    output.mkdir(exist_ok=False)
    records = []
    for archive in archives:
        with tarfile.open(archive, "r:") as source:
            for member in source:
                if not member.isfile() or not member.name.endswith(".apk"):
                    continue
                raw = source.extractfile(member).read()
                apk_hash = digest(raw)
                name = archive.stem + "-" + hashlib.sha256(member.name.encode()).hexdigest()[:16]
                target = output / (name + ".apk")
                with target.open("xb") as stream:
                    stream.write(raw)
                target.chmod(0o444)
                record = dict(archive=str(archive), member=member.name,
                              bytes=len(raw), sha256=apk_hash, extracted=str(target))
                with zipfile.ZipFile(io.BytesIO(raw)) as apk:
                    record["zip_crc_valid"] = apk.testzip() is None
                    entries = [n for n in apk.namelist() if n.endswith("/libscope-auklet.so")]
                    for entry in entries:
                        native = apk.read(entry)
                        native_target = output / (name + "-" + entry.split("/")[-2] + ".so")
                        with native_target.open("xb") as stream:
                            stream.write(native)
                        native_target.chmod(0o444)
                        records.append(dict(archive=str(archive), apk_member=member.name,
                                            member=entry, bytes=len(native), sha256=digest(native),
                                            extracted=str(native_target), kind="native"))
                record["kind"] = "apk"
                records.append(record)
    lines = ["schema_version = 1"]
    for record in records:
        lines.append("[[artifacts]]")
        lines.extend(f"{key} = {json.dumps(value)}" for key, value in record.items())
    (output / "manifest.toml").write_text("\n".join(lines) + "\n")
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("archives", nargs="+", type=Path)
    args = parser.parse_args()
    records = inspect(args.archives, args.output)
    print(f"Preserved {len(records)} APK/native records; see manifest.toml.")


if __name__ == "__main__":
    main()
