#!/usr/bin/env python3
"""Compile the actual C resolver for the host and compare with the Python oracle."""
import argparse
import ctypes
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile


def load(name, path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--apk',type=Path,required=True)
    p.add_argument('--maps',type=Path,required=True)
    p.add_argument('--mapped-path',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assert not a.output.exists()
    oracle=load('apk_oracle',Path(__file__).with_name('resolve-apk-cached-identity.py'))
    data=a.apk.read_bytes();start,size,loads=oracle.archive_entry(data)
    rows=oracle.v.maps_rows(a.maps.read_text());identities={(r['major'],r['minor'],r['inode']) for r in rows if r['path']==a.mapped_path}
    assert len(identities)==1;identity=next(iter(identities))
    source='#define READER_HOST_TEST\n'+a.source.read_text()+'''
int resolve_control(const char *text,const char *path,U dev,U ino,U *bias) {
 return resolve_maps(text,path,dev,ino,bias);
}
int elf_control(const unsigned char *p) { return validate_elf(p,512); }
void hash_control(const unsigned char *p,U n,char *out) { hash_bytes(p,n,out); }
'''
    with tempfile.TemporaryDirectory(prefix='apk-reader-controls-') as d:
        root=Path(d);(root/'control.c').write_text(source)
        cmd=['cc','-dynamiclib','-O2','-o',str(root/'control.dylib'),str(root/'control.c')]
        subprocess.run(cmd,check=True,capture_output=True)
        dll=ctypes.CDLL(str(root/'control.dylib'))
        resolve=dll.resolve_control;resolve.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong)];resolve.restype=ctypes.c_int
        original=oracle.resolve_apk;comparisons=[]
        def checked(rs,path,ident,off,length,segments):
            # C is deliberately pinned to one entry. A wrong request offset must be rejected by the Python contract.
            if off!=start:return original(rs,path,ident,off,length,segments)
            text=''.join(f'{r["start"]:x}-{r["end"]:x} {r["perms"]} {r["offset"]:08x} {r["major"]:02x}:{r["minor"]:02x} {r["inode"]} {r["path"]}\n' for r in rs)
            major,minor,inode=ident
            dev=((major&0xfff)<<8)|(minor&255)|((minor&~255)<<12)|((major&~0xfff)<<32)
            bias=ctypes.c_ulong();ok=resolve(text.encode(),path.encode(),dev,inode,ctypes.byref(bias))
            try:prediction=original(rs,path,ident,off,length,segments)
            except ValueError:
                assert not ok,'C accepted Python rejection';comparisons.append(False);raise
            assert ok and bias.value==prediction[0],'C/Python bias disagreement'
            comparisons.append(True);return prediction
        oracle.resolve_apk=checked
        checked(rows,a.mapped_path,identity,start,size,loads)
        negatives=oracle.controls(data,rows,a.mapped_path,identity,start,size,loads)
        dll.elf_control.argtypes=[ctypes.c_char_p];dll.elf_control.restype=ctypes.c_int
        assert dll.elf_control(data[start:start+512])==1
        bad=bytearray(data[start:start+512]);bad[18]^=1;assert dll.elf_control(bytes(bad))==0
        dll.hash_control.argtypes=[ctypes.c_char_p,ctypes.c_ulong,ctypes.c_void_p]
        for payload in (data,data[start:start+size]):
            out=ctypes.create_string_buffer(65);dll.hash_control(payload,len(payload),out)
            assert out.value.decode()==oracle.v.sha(payload)
    result=dict(schema_version=1,source_sha256=oracle.v.sha(a.source.read_bytes()),
                verifier_sha256=oracle.v.sha(Path(__file__).read_bytes()),
                python_controls=len(negatives),c_mapping_comparisons=len(comparisons),
                c_mapping_positive=sum(comparisons),c_mapping_negative=len(comparisons)-sum(comparisons),
                c_elf_controls=2,c_sha256_controls=2,physical_access=False)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(''.join(k+' = '+json.dumps(v)+'\n' for k,v in result.items()))
    print(json.dumps(result))


if __name__=='__main__':main()
