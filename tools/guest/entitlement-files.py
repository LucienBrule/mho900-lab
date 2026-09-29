#!/usr/bin/env python3
"""Hash a private fixture tree without dereferencing links or accepting special files."""
import hashlib
from pathlib import Path
import stat
import sys


def quoted(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r') + '"'


root = Path(sys.argv[1]).absolute()
if root.is_symlink() or not root.is_dir():
    raise SystemExit("Expected a regular fixture directory")
print('schema_version = "mho900-lab.private-file-tree/1"')
for path in sorted(root.rglob('*')):
    info = path.lstat()
    if stat.S_ISDIR(info.st_mode):
        continue
    if not stat.S_ISREG(info.st_mode):
        raise SystemExit("Fixture contains a link or special file")
    before = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    after = path.stat()
    if before != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise SystemExit("File changed while hashing")
    print('\n[[files]]')
    print('path = ' + quoted(path.relative_to(root).as_posix()))
    print('bytes = ' + str(info.st_size))
    print('mode = ' + quoted(oct(stat.S_IMODE(info.st_mode))))
    print('sha256 = ' + quoted(digest))
