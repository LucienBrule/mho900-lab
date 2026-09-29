#!/usr/bin/env python3
"""Run offline transaction controls and compile the ARM64 layout assertions."""
import argparse
import hashlib
import pathlib
import subprocess
p = argparse.ArgumentParser()
p.add_argument('--output', type=pathlib.Path, required=True)
p.add_argument('--host-cc', default='clang')
p.add_argument('--cross-cc', required=True)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
source = pathlib.Path(__file__).resolve().parent
commands = [
    [a.host_cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined', str(source/'test-fram-read.c'), '-o', str(a.output/'controls')],
    [str((a.output/'controls').resolve())],
]
probe = a.output/'abi-probe.c'
probe.write_text('#include "fram-read.h"\nint probe(fram_transfer f, void *c, uint8_t *p, size_t *n) { return fram_image(f,c,p,n); }\n')
commands.append([a.cross_cc, '--target=aarch64-linux-android25', '-ffreestanding', '-std=c11', '-Wall', '-Wextra', '-Werror', '-I'+str(source), '-c', str(probe), '-o', str(a.output/'abi-probe.o')])
for index, command in enumerate(commands):
    result = subprocess.run(command, capture_output=True)
    (a.output/f'step-{index}.stdout').write_bytes(result.stdout)
    (a.output/f'step-{index}.stderr').write_bytes(result.stderr)
    if result.returncode:
        raise SystemExit(f'step {index} failed with {result.returncode}')
(a.output/'result.toml').write_text('schema_version = 1\nclassification = "offline-controls-only"\nhost_controls = true\narm64_layout_compile = true\ndevice_contact = false\n')
(a.output/'source-sha256.toml').write_text('schema_version = 1\n' + ''.join('\n[[files]]\npath = \"tools/guest/fram-contract/' + x.name + '\"\nsha256 = \"' + hashlib.sha256(x.read_bytes()).hexdigest() + '\"\n' for x in sorted(source.iterdir()) if x.is_file()))
files = sorted(x for x in a.output.iterdir() if x.is_file())
(a.output/'SHA256SUMS').write_text(''.join(hashlib.sha256(x.read_bytes()).hexdigest()+'  '+x.name+'\n' for x in files))
print('Offline controls and ARM64 compile passed')
