#!/usr/bin/env python3
"""Prepare private specimen-derived inputs and a frozen guest protocol source.

Python provides the existing TOML, hash and protocol composition tools. No device
connection or key/token generation occurs. Unit material stays in the output.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tomllib


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sealed(root, index, relative):
    p = root / relative
    lines = (root / index).read_text().splitlines()
    assert any(line.split()[0] == sha(p) and line.split(maxsplit=1)[1].lstrip('*').endswith(relative)
               for line in lines), 'input seal mismatch: ' + relative
    return p.read_bytes()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ('art-fixture', 'coherence', 'idn-run', 'output'):
        p.add_argument('--'+arg, type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists()
    cipher = sealed(a.coherence, 'evidence-sha256.txt', 'Key.data')
    plain = sealed(a.coherence, 'evidence-sha256.txt', 'Key.decoded.bin')
    sample = sealed(a.coherence, 'evidence-sha256.txt', 'sample.bin')
    coherence = tomllib.loads(sealed(a.coherence, 'evidence-sha256.txt', 'result.toml').decode())
    assert coherence['result'] == 'accepted' and coherence['physical_derivation_matches']
    response_path = a.idn_run/'response.bin'
    manifest = tomllib.loads((a.idn_run/'sealed/manifest.toml').read_text())
    assert any(x['path'].endswith('response.bin') and x['sha256'] == sha(response_path)
               for x in manifest['artifacts']), 'IDN response seal mismatch'
    response = response_path.read_bytes()
    identity = response.decode('ascii').strip().split(',')
    left, right = plain.rstrip(b'\0').split(b';')
    assert len(identity) == 4 and identity[1].strip() == 'MHO984'
    # Recovered verifier ignores its left-field argument; startup requires it nonempty.
    # Preserve public identity and file metadata separately rather than forcing equality.
    assert left and identity[2].strip()
    assert len(right) == 130 and len(cipher) == 148 and len(sample) == 24
    a.output.mkdir(parents=True, mode=0o700)
    for name in ('lib', 'art'):
        assert not any(x.is_symlink() for x in (a.art_fixture/name).rglob('*'))
        shutil.copytree(a.art_fixture/name, a.output/name)
    shutil.copy2(a.art_fixture/'ramdisk.img', a.output/'ramdisk.img')
    (a.output/'rigol/data').mkdir(parents=True)
    (a.output/'rigol/data/Key.data').write_bytes(cipher)
    (a.output/'model').mkdir()
    cfg = dict(schema_version=2, model='MHO984', serial=identity[2].strip(),
               key_left=left.decode('ascii'),
               dna_hex=f'{int.from_bytes(sample[:8], "little"):016x}', file_keys_hex=sample[8:].hex(),
               key_field_hex=right.hex(), key_ciphertext_hex=cipher.hex(),
               private_store='fresh-modeled', physical_contact=False)
    (a.output/'acquired.toml').write_text(''.join(k+' = '+json.dumps(v)+'\n' for k,v in cfg.items()))
    source = Path(__file__).parent
    parts = ['entitlement-private-store.js', 'entitlement-art.js',
             'entitlement-acquired-baseline.js', 'entitlement-baseline.js']
    (a.output/'entitlement.js').write_text('const acquiredKeyFixture = '+json.dumps(cfg)+';\n'+
                                        '\n'.join((source/name).read_text() for name in parts))
    manifest = dict(schema_version=1, physical_contact=False, specimen_private_fram=False,
                    public_identity_from_physical_idn=True, key_left_preserved_separately=True,
                    key_left_equals_public_serial=left.decode('ascii') == identity[2].strip(), coherent_acquired_key=True,
                    library_sha256=sha(a.output/'lib/libscope-auklet.so'),
                    key_ciphertext_sha256=hashlib.sha256(cipher).hexdigest(),
                    idn_response_sha256=hashlib.sha256(response).hexdigest())
    (a.output/'preparation.toml').write_text(''.join(k+' = '+json.dumps(v)+'\n' for k,v in manifest.items()))
    (a.output/'preparer.py').write_bytes(Path(__file__).read_bytes())
    for name in parts:
        (a.output/name).write_bytes((source/name).read_bytes())
    files = sorted(x for x in a.output.rglob('*') if x.is_file())
    (a.output/'evidence-sha256.txt').write_text(''.join(sha(x)+'  '+str(x.relative_to(a.output))+'\n' for x in files))
    print('Private acquired-key baseline prepared; public serial and key metadata preserved separately.')


if __name__ == '__main__':
    main()
