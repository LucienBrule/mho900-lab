#!/usr/bin/env python3
"""Create the separate fixed derived-library bandwidth profile from a pinned reader."""
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path

BASE_SHA = '1a49ad8d0577cf4b29fa69d686df587e995fa3d9eec7cb7178689613aa657438'
DERIVED_SHA = '09689a442e8d285775b37089a8d631e1e445fe03d3499e830cdcc8f32439504e'
CC_SHA = '8daf964b5d524b4754d4300f370d9956a1de8f3815ce5828bb8fd8ad087b0b78'
LD_SHA = '1f80841d925f7b7d875d88e593e6e12dd496ab9227fc60f6ce9b07f73df6c81e'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('cc','ld','elf','output'): p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();src=Path(__file__).resolve().parent;base=src.parent/'read-cached-identity.c'
    assert sha(base)==BASE_SHA and sha(a.elf)==DERIVED_SHA and sha(a.cc)==CC_SHA and sha(a.ld)==LD_SHA
    assert not a.output.exists()
    s=base.read_text()
    def replace(old,new,n=1):
        nonlocal s
        assert s.count(old)==n,(old,s.count(old),n)
        s=s.replace(old,new)
    replace('Fixed stock-library cached-data reader','Fixed derived-library cached-bandwidth reader')
    replace('4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e',DERIVED_SHA)
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
    s=s.replace('DNA','RAW_BAND').replace('KEYS','EFFECTIVE_BAND').replace('dna','raw_band').replace('keys','effective_band').replace('file_effective_band','effective_band')
    s=s.replace('mho900-lab.cached-identity-reader/1','mho900-lab.derived-bandwidth-reader/1')
    assert all(x not in s for x in ['0xbbccf0','0xbbcd1c','file_keys','dna_address','sample[2][24]'])
    a.output.mkdir(parents=True)
    (a.output/'read-derived-bandwidth.c').write_text(s)
    shutil.copy2(src/'fixture.c',a.output/'derived-bandwidth-fixture.c')
    shutil.copy2(base,a.output/'predecessor.c');shutil.copy2(__file__,a.output/'build.py')
    shutil.copy2(a.elf,a.output/'libscope-auklet.so')
    for name in ('read-derived-bandwidth','derived-bandwidth-fixture'):
        subprocess.run([str(a.cc),'--target=aarch64-linux-gnu','-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib','-static','-fno-pic','-Werror','-Wall','-Wextra','--ld-path='+str(a.ld),'-Wl,-e,_start','-Wl,--build-id=sha1','-o',str(a.output/name),str(a.output/(name+'.c'))],check=True)
    text='schema = "mho900-lab.derived-bandwidth-build/1"\nprofile = "derived-bandwidth-4-4"\nmaximum_memory_bytes = 16\n'
    for k,v in dict(predecessor_sha256=BASE_SHA,derived_library_sha256=DERIVED_SHA,compiler_sha256=CC_SHA,linker_sha256=LD_SHA).items():text+=k+' = '+json.dumps(v)+'\n'
    for f in sorted(a.output.iterdir()):text+='\n[[files]]\npath = '+json.dumps(f.name)+'\nsha256 = '+json.dumps(sha(f))+'\n'
    (a.output/'build.toml').write_text(text)
    print('Built fixed derived two-word reader and nonexecuting mapping fixture.')


if __name__=='__main__':main()
