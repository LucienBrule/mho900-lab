#!/usr/bin/env python3
"""Build and host-test the fixed read-only FRAM acquisition wrapper; never opens a device."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('cc','ld','host-cc','output'):p.add_argument('--'+n,required=True,type=Path)
 a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 source=Path(__file__).resolve().parent
 flags=['-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib','-static','-fno-pic','-Werror','-Wall','-Wextra']
 subprocess.run([str(a.cc),'--target=aarch64-linux-gnu',*flags,'--ld-path='+str(a.ld),'-Wl,-e,_start','-Wl,--build-id=sha1','-o',str(a.output/'read-fram'),str(source/'read-fram.c')],check=True)
 subprocess.run([str(a.host_cc),'-std=c11','-Wall','-Wextra','-Werror',str(source/'test-reader.c'),'-o',str(a.output/'test-reader')],check=True)
 r=subprocess.run([str(a.output.resolve()/'test-reader')],capture_output=True,text=True,check=True)
 (a.output/'controls.toml').write_text('schema_version = 1\n'+r.stdout+'cases = ["equal-images", "wrong-device-number", "short-result", "ioctl-failure", "differing-images", "non-character-device", "journal-short-write", "journal-fsync-failure", "image-write-failure", "device-open-failure", "device-fstat-failure"]\nphysical_contact = false\nguest_execution = false\n')
 for n in ('read-fram.c','test-reader.c','build.py'):shutil.copy2(source/n,a.output/n)
 shutil.copy2(source.parent/'fram-contract/fram-read.h',a.output/'fram-read.h')
 t='schema_version = 1\nprofile = "fram-reader-two-images"\nmaximum_transactions = 1024\nmaximum_read_bytes = 16384\nmaximum_selector_bytes = 2048\n'
 for n,v in [('compiler',a.cc),('linker',a.ld),('host_compiler',a.host_cc)]:t+=n+'_sha256 = '+json.dumps(sha(v))+'\n'
 for f in sorted(a.output.iterdir()):
  if f.name!='build.toml':t+='\n[[files]]\npath = '+json.dumps(f.name)+'\nsha256 = '+json.dumps(sha(f))+'\n'
 (a.output/'build.toml').write_text(t)
 print('built = true\nhost_controls_passed = true')
if __name__=='__main__':main()
