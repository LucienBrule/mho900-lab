#!/usr/bin/env python3
"""Build a fixed two-word observation profile from the pinned APK reader source."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('base-build','cc','ld','output'): p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();base=a.base_build
    assert sha(base/'read-apk-cached-identity.c')=='b3bd494cff5c8d94c73d0c1532bb47967964478c683a270824d79dc365c5ef68'
    assert sha(base/'apk-cached-mapping-fixture.c')=='ac562a02dfe87166447fb5fcd6fa0ba51f9685561f4726f8a11348191c128a4d'
    assert sha(a.cc)=='8daf964b5d524b4754d4300f370d9956a1de8f3815ce5828bb8fd8ad087b0b78'
    assert sha(a.ld)=='1f80841d925f7b7d875d88e593e6e12dd496ab9227fc60f6ce9b07f73df6c81e'
    assert not a.output.exists()
    s=(base/'read-apk-cached-identity.c').read_text()
    def replace(old,new,n=1):
        nonlocal s
        assert s.count(old)==n,(old,s.count(old),n)
        s=s.replace(old,new)
    replace('0xbbccf0UL','0xbbcce4UL');replace('0xbbcd1cUL','0xbbcce8UL')
    replace('b + dna_va + 8','b + dna_va + 4');replace('b + keys_va + 16','b + keys_va + 4')
    replace('== 0xbbbcf0','== 0xbbbce4');replace('== 0xbbbd1c','== 0xbbbce8')
    replace('sample[2][24]','sample[2][8]')
    replace('numfield("dna_size", 8)','numfield("dna_size", 4)');replace('numfield("file_keys_size", 16)','numfield("file_keys_size", 4)')
    replace('numfield("maximum_memory_bytes", 48)','numfield("maximum_memory_bytes", 16)')
    replace('uintout(i % 2 ? 16 : 8, 10)','uintout(4, 10)')
    replace('U sizes[2] = {8, 16}','U sizes[2] = {4, 4}')
    replace('(i ? 8 : 0)','(i ? 4 : 0)');replace('i ? 8 + (r > 0','i ? 4 + (r > 0')
    replace('sample[round], 24','sample[round], 8',2);replace('sample[0], sample[1], 24','sample[0], sample[1], 8')
    # Semantic names are changed only after exact structural edits.
    s=s.replace('DNA','RAW_BAND').replace('KEYS','EFFECTIVE_BAND').replace('dna','raw_band').replace('keys','effective_band')
    s=s.replace('file_effective_band','effective_band')
    assert 'mho900-lab.cached-identity-reader/1' in s
    s=s.replace('mho900-lab.cached-identity-reader/1','mho900-lab.apk-bandwidth-reader/1')
    fixture=(base/'apk-cached-mapping-fixture.c').read_text()
    fixture=fixture.replace('i<8;i++','i<4;i++').replace('i<16;i++','i<4;i++').replace('0xbbccf0','0xbbcce4').replace('0xbbcd1c','0xbbcce8')
    a.output.mkdir(parents=True)
    # Keep predecessor executable basenames for the existing fixture controller.
    (a.output/'read-apk-cached-identity.c').write_text(s)
    (a.output/'apk-cached-mapping-fixture.c').write_text(fixture)
    shutil.copy2(__file__,a.output/'build.py')
    for name in ('read-apk-cached-identity','apk-cached-mapping-fixture'):
        subprocess.run([str(a.cc),'--target=aarch64-linux-gnu','-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib','-static','-fno-pic','-Werror','-Wall','-Wextra','--ld-path='+str(a.ld),'-Wl,-e,_start','-Wl,--build-id=sha1','-o',str(a.output/name),str(a.output/(name+'.c'))],check=True)
    text='schema_version = 1\nprofile = "cached-bandwidth-4-4"\nmaximum_memory_bytes = 16\n'
    for f in sorted(a.output.iterdir()):
        text+='\n[[files]]\npath = '+json.dumps(f.name)+'\nsha256 = '+json.dumps(sha(f))+'\n'
    (a.output/'build.toml').write_text(text)


if __name__=='__main__': main()
