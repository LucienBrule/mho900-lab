#!/usr/bin/env python3
"""Offline stock ARM64 identity/XXTEA execution using Unicorn, with a separate word model.

Unicorn is the reason for Python here. No network, guest or device interface is used.
Unit values and decoded data are written only into the supplied private output directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import tarfile
import tomllib
import unicorn
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_PROT_READ,UC_PROT_WRITE,UC_PROT_EXEC
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X30,UC_ARM64_REG_SP,UC_ARM64_REG_PC,UC_ARM64_REG_TPIDR_EL0

STOCK='4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e'
MASK=(1<<32)-1
BASE=0x10000000
STACK=0x20000000
DATA=0x21000000
TLS=0x22000000
STOP=0x23000000
ALLOWED=[(0x42a91c,0x42a9e0),(0x42f254,0x42f2b0),(0x42f640,0x42f658),
         (0x3be7e4,0x3bed94),(0x1f8520,0x1f8530)]


def sha(b):return hashlib.sha256(b).hexdigest()
def write_toml(path,values):
    with path.open('x') as f:
        for k,v in values.items():f.write(k+' = '+json.dumps(v)+'\n')


def derive(dna):
    if dna==(1<<64)-1:return b'\xff'*16
    return struct.pack('<4I',dna&MASK,(dna^(dna>>1))&MASK,dna&MASK,dna>>32)


def tea(data,key,decode):
    assert len(data)%4==0 and len(data)>=8 and len(key)==16
    words=list(struct.unpack('<'+'I'*(len(data)//4),data));k=struct.unpack('<4I',key);n=len(words)
    rounds=6+52//n
    def mix(z,y,total,p,e):
        return ((((z>>5)^((y<<2)&MASK))+((y>>3)^((z<<4)&MASK))) ^ ((total^y)+(k[(p&3)^e]^z))) & MASK
    if decode:
        total=(rounds*0x9e3779b9)&MASK;y=words[0]
        for _ in range(rounds):
            e=(total>>2)&3
            for p in range(n-1,0,-1):
                z=words[p-1];words[p]=(words[p]-mix(z,y,total,p,e))&MASK;y=words[p]
            z=words[-1];words[0]=(words[0]-mix(z,y,total,0,e))&MASK;y=words[0]
            total=(total-0x9e3779b9)&MASK
    else:
        total=0;z=words[-1]
        for _ in range(rounds):
            total=(total+0x9e3779b9)&MASK;e=(total>>2)&3
            for p in range(n-1):
                y=words[p+1];words[p]=(words[p]+mix(z,y,total,p,e))&MASK;z=words[p]
            y=words[0];words[-1]=(words[-1]+mix(z,y,total,n-1,e))&MASK;z=words[-1]
    return struct.pack('<'+'I'*n,*words)


class Stock:
    def __init__(self,blob):
        assert sha(blob)==STOCK
        self.u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u=self.u
        u.mem_map(BASE,0x3cb5000,UC_PROT_READ|UC_PROT_WRITE)
        u.mem_write(BASE,blob[:0xb689d4]);u.mem_write(BASE+0xb69c00,blob[0xb68c00:0xbe0000])
        # Three symbol relocations, corroborated by the stock ELF relocation table.
        for got,target in [(0xb8d758,0xbbccf0),(0xb8cc20,0x151b350),(0xb78968,0x3be8bc)]:
            u.mem_write(BASE+got,struct.pack('<Q',BASE+target))
        u.mem_protect(BASE,0xb69000,UC_PROT_READ|UC_PROT_EXEC)
        for addr,size in [(STACK,0x10000),(DATA,0x10000),(TLS,0x1000)]:u.mem_map(addr,size,UC_PROT_READ|UC_PROT_WRITE)
        u.mem_map(STOP,0x1000,UC_PROT_READ|UC_PROT_EXEC)
        u.reg_write(UC_ARM64_REG_TPIDR_EL0,TLS)
        self.trace=[];self.executions=[]
        def code(uc,address,size,_):
            off=address-BASE
            assert any(lo<=off<hi for lo,hi in ALLOWED),'unmodeled execution boundary at '+hex(off)
            self.trace.append(off)
        def write(uc,access,address,size,value,_):
            assert any(lo<=address and address+size<=hi for lo,hi in [(STACK,STACK+0x10000),(DATA,DATA+0x10000),(BASE+0x151b350,BASE+0x151b360)]),'unexpected stock write at '+hex(address-BASE)
        u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
    def call(self,entry,x0=0,x1=0):
        u=self.u;u.reg_write(UC_ARM64_REG_SP,STACK+0xff00);u.reg_write(UC_ARM64_REG_X30,STOP)
        u.reg_write(UC_ARM64_REG_X0,x0);u.reg_write(UC_ARM64_REG_X1,x1)
        before=len(self.trace);u.emu_start(BASE+entry,STOP,timeout=2000000,count=1000000)
        assert u.reg_read(UC_ARM64_REG_PC)==STOP,'instruction/time budget or unexpected stop'
        self.executions.append((entry,len(self.trace)-before));return u.reg_read(UC_ARM64_REG_X0)
    def derive(self,dna):
        self.u.mem_write(BASE+0xbbccf0,struct.pack('<Q',dna));self.u.mem_write(DATA,b'\x00'*16)
        self.call(0x42a91c,DATA);return bytes(self.u.mem_read(DATA,16))
    def crypt(self,data,key,decode):
        assert len(data)<=0xf000
        self.u.mem_write(DATA,key);self.call(0x3be7e4,DATA)
        self.u.mem_write(DATA+0x100,data)
        assert self.call(0x3bed50 if decode else 0x3be880,DATA+0x100,len(data))==0
        return bytes(self.u.mem_read(DATA+0x100,len(data)))


def shape(data):
    text=data.split(b'\0',1)[0]
    parts=text.split(b';')
    return dict(decoded_bytes=len(data),text_bytes=len(text),semicolon_fields=len(parts),
                field_lengths=[len(x) for x in parts],printable_text=all(32<=b<127 for b in text),
                trailing_zero_bytes=len(data)-len(data.rstrip(b'\0')),
                second_field_is_32_bytes=len(parts)==2 and len(parts[1])==32)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['library','sample','sample-repeat','archive','archive-index','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();assert not a.output.exists();a.output.mkdir(parents=True,mode=0o700);out=a.output
    result='failed';error='';summary={}
    try:
        blob=a.library.read_bytes();assert sha(blob)==STOCK
        sample=a.sample.read_bytes();assert len(sample)==24 and sample==a.sample_repeat.read_bytes()
        archive_hash=sha(a.archive.read_bytes());index=a.archive_index.read_text()
        assert any(line.split()[0]==archive_hash and line.rstrip().endswith('logical/rigol.tar') for line in index.splitlines()),'archive seal mismatch'
        with tarfile.open(a.archive) as archive:
            members=[m for m in archive if m.name=='rigol/data/Key.data'];assert len(members)==1 and members[0].isfile()
            cipher=archive.extractfile(members[0]).read()
        assert len(cipher)%4==0 and len(cipher)>=8
        (out/'Key.data').write_bytes(cipher);(out/'sample.bin').write_bytes(sample)
        write_toml(out/'inputs.toml',dict(library_sha256=sha(blob),sample_sha256=sha(sample),archive_sha256=archive_hash,
                   archive_member='rigol/data/Key.data',key_data_sha256=sha(cipher),key_data_bytes=len(cipher),
                   source_sha256=sha(Path(__file__).read_bytes()),unicorn_version=unicorn.__version__))
        cpu=Stock(blob)
        controls=[0,1,0xffffffff,1<<63,0x0123456789abcdef,(1<<64)-1]
        for dna in controls:assert cpu.derive(dna)==derive(dna),'synthetic derivation mismatch'
        dna=int.from_bytes(sample[:8],'little');observed=sample[8:]
        predicted=cpu.derive(dna);assert predicted==derive(dna)==observed,'physical cached key mismatch'
        # Independent known synthetic word-model/native control, not acquired material.
        plain=b'fixture;'+b'0123456789abcdef0123456789abcdef'
        synthetic_key=derive(0x0123456789abcdef)
        synthetic_cipher=cpu.crypt(plain,synthetic_key,False)
        assert synthetic_cipher==tea(plain,synthetic_key,False)
        assert cpu.crypt(synthetic_cipher,synthetic_key,True)==tea(synthetic_cipher,synthetic_key,True)==plain
        decoded=cpu.crypt(cipher,observed,True);assert decoded==tea(cipher,observed,True),'native/reference decode disagreement'
        (out/'Key.decoded.bin').write_bytes(decoded)
        assert cpu.crypt(decoded,observed,False)==tea(decoded,observed,False)==cipher,'ciphertext re-encode mismatch'
        wrong=bytes([observed[0]^1])+observed[1:]
        wrong_plain=cpu.crypt(cipher,wrong,True);assert wrong_plain==tea(cipher,wrong,True)
        write_toml(out/'decoded-shape.toml',shape(decoded));write_toml(out/'wrong-key-shape.toml',shape(wrong_plain))
        summary=dict(derivation_controls=len(controls),physical_derivation_matches=True,native_reference_decode_equal=True,
                     exact_reencode=True,wrong_key_changes_plaintext=wrong_plain!=decoded,**shape(decoded))
        (out/'instruction-trace.txt').write_text(''.join(hex(x)+'\n' for x in cpu.trace))
        (out/'calls.toml').write_text(''.join('[[calls]]\nentry = '+json.dumps(hex(entry))+'\ninstructions = '+str(n)+'\n' for entry,n in cpu.executions))
        result='accepted'
    except BaseException as exc:
        import traceback
        error=str(exc);(out/'failure.txt').write_text(traceback.format_exc())
    write_toml(out/'result.toml',dict(schema_version=1,result=result,error=error,physical_access=False,**summary))
    print((out/'result.toml').read_text())
    return 0 if result=='accepted' else 1


if __name__=='__main__':raise SystemExit(main())
