#!/usr/bin/env python3
"""Hash input files and directory contents, rejecting ambiguous source objects."""
import hashlib
from pathlib import Path
import sys


def inventory(paths):
    files = []
    for path in paths:
        if path.is_dir():
            for child in sorted(path.rglob('*')):
                if child.is_symlink():
                    raise ValueError('Symlink in input directory')
                if child.is_file():
                    files.append(child)
                elif not child.is_dir():
                    raise ValueError('Unsupported input object')
        elif path.is_file():
            files.append(path)
        else:
            raise ValueError('Unsupported input argument')
    rows = []
    for path in files:
        if any(c in str(path) for c in '\n\r\\'):
            raise ValueError('Unsupported input filename')
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        rows.append(f'{digest}  {path}\n')
    return ''.join(rows)


if __name__ == '__main__':
    sys.stdout.write(inventory([Path(arg) for arg in sys.argv[1:]]))
