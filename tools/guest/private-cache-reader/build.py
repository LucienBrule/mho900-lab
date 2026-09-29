#!/usr/bin/env python3
"""Build the bounded passive cache reader and deterministic mapping control."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('base-build','cc','ld','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args()
 assert sha(a.base_build/'read-apk-cached-identity.c')=='e0a4aede72056dc2b5d38309bafa6fab31c99e3ed8c1de5751a00f5cfe4df422'
 assert sha(a.base_build/'apk-cached-mapping-fixture.c')=='ec8de7830159bb61b80847a45cafced06600a6355331ee072b917673ca8c0a2a'
 assert sha(a.cc)=='8daf964b5d524b4754d4300f370d9956a1de8f3815ce5828bb8fd8ad087b0b78'
 assert sha(a.ld)=='1f80841d925f7b7d875d88e593e6e12dd496ab9227fc60f6ce9b07f73df6c81e'
 assert not a.output.exists()
 a.output.mkdir(parents=True)
 source=Path(__file__).resolve().parent
 for name in ('read-private-cache','private-cache-mapping-fixture'):
  shutil.copy2(source/(name+'.c'),a.output/(name+'.c'))
  subprocess.run([str(a.cc),'--target=aarch64-linux-gnu','-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib','-static','-fno-pic','-Werror','-Wall','-Wextra','--ld-path='+str(a.ld),'-Wl,-e,_start','-Wl,--build-id=sha1','-o',str(a.output/name),str(a.output/(name+'.c'))],check=True)
 shutil.copy2(__file__,a.output/'build.py')
 text='schema_version = 1\nprofile = "private-cache-owner-two-snapshot"\nmaximum_memory_bytes = 16384\nmaximum_registry_active = 64\nmaximum_registry_capacity = 128\nprivate_window_bytes = 1792\nphysical_contact = false\nguest_execution = false\n'
 text+='compiler_sha256 = '+json.dumps(sha(a.cc))+'\nlinker_sha256 = '+json.dumps(sha(a.ld))+'\n'
 for f in sorted(a.output.iterdir()):text+='\n[[files]]\npath = '+json.dumps(f.name)+'\nsha256 = '+json.dumps(sha(f))+'\n'
 (a.output/'build.toml').write_text(text)
 print('built = true\nmaximum_memory_bytes = 16384')
if __name__=='__main__':main()
