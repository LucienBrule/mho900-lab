#!/usr/bin/env python3
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('cc','ld','host-cc','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.output.mkdir(parents=True);src=Path(__file__).resolve().parent
 subprocess.run([str(a.cc),'--target=aarch64-linux-gnu','-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-nostdlib','-static','-fno-pic','-Werror','-Wall','-Wextra','--ld-path='+str(a.ld),'-Wl,-e,_start','-Wl,--build-id=sha1','-o',str(a.output/'stat-node'),str(src/'stat-node.c')],check=True)
 subprocess.run([str(a.host_cc),'-std=c11','-Wall','-Wextra','-Werror',str(src/'test-stat-node.c'),'-o',str(a.output/'test-stat-node')],check=True)
 r=subprocess.run([str(a.output.resolve()/'test-stat-node')],capture_output=True,text=True,check=True);(a.output/'controls.toml').write_text(r.stdout)
 for n in ('stat-node.c','test-stat-node.c','build-stat.py'):shutil.copy2(src/n,a.output/n)
 t='schema_version = 1\nprofile = "fram-stat-node"\n'
 for n,v in [('compiler',a.cc),('linker',a.ld),('host_compiler',a.host_cc)]:t+=n+'_sha256 = '+json.dumps(sha(v))+'\n'
 for f in sorted(a.output.iterdir()):t+='\n[[files]]\npath = '+json.dumps(f.name)+'\nsha256 = '+json.dumps(sha(f))+'\n'
 (a.output/'build.toml').write_text(t)
if __name__=='__main__':main()
