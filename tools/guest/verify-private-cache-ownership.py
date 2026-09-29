#!/usr/bin/env python3
"""Bounded stock ELF ownership evidence extraction; no process or device access."""
from pathlib import Path
import argparse,hashlib,re,struct,json
p=argparse.ArgumentParser();p.add_argument('--elf',type=Path,required=True);p.add_argument('--assembly',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
b=a.elf.read_bytes();pin=hashlib.sha256(b).hexdigest();assert pin=='4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e'
po=struct.unpack_from('<Q',b,32)[0];ps,pn=struct.unpack_from('<HH',b,54);segments=[]
for i in range(pn):
 t,f,o,v,p,sz,ms,al=struct.unpack_from('<IIQQQQQQ',b,po+i*ps)
 if t==1:segments.append((v,o,sz))
def at(va,n):
 m=[o+va-v for v,o,sz in segments if v<=va and va+n<=v+sz];assert len(m)==1
 return b[m[0]:m[0]+n]
so=struct.unpack_from('<Q',b,40)[0];ss,sn,si=struct.unpack_from('<HHH',b,58);sections=[struct.unpack_from('<IIQQQQIIQQ',b,so+i*ss) for i in range(sn)]
def content(i):s=sections[i];return b[s[4]:s[4]+s[5]]
def string(x,o):return x[o:x.index(0,o)].decode()
syms={};arrays={}
for i,s in enumerate(sections):
 if s[1]!=11:continue
 st=content(s[6]);arr=[]
 for o in range(s[4],s[4]+s[5],s[9]):
  n,info,other,sh,v,size=struct.unpack_from('<IBBHQQ',b,o);name=string(st,n);arr.append((name,v,size));syms[name]=(v,size)
 arrays[i]=arr
relocs={}
for s in sections:
 if s[1]!=4 or s[6] not in arrays:continue
 for o in range(s[4],s[4]+s[5],s[9]):
  va,info,add=struct.unpack_from('<QQq',b,o);relocs[va]=(info&0xffffffff,arrays[s[6]][info>>32],add)
wanted={'_ZN8CApiBase9_servListE':(0xbe0f18,24),'_ZN11CApiFactory13g_ServiceListE':(0xbe0e60,24),'_ZTV9CApiSetup':(0xb6c3a0,160),'_ZTI9CApiSetup':(0xb6c440,56),'_ZN9CApiSetup12mPrivateDataE':(0x151b3f0,32)}
for name,value in wanted.items():assert syms[name]==value
for va,symbol in [(0xb8e0b8,'_ZN8CApiBase9_servListE'),(0xb8c930,'_ZTV9CApiSetup')]:
 typ,sym,add=relocs[va];assert typ==1025 and sym[0]==symbol and add==0
for va,offset in [(0xb6c3a0,0),(0xb6c3e0,-8),(0xb6c408,-72)]:
 assert struct.unpack('<q',at(va,8))[0]==offset
 typ,sym,add=relocs[va+8];assert typ==257 and sym[0]=='_ZTI9CApiSetup' and add==0
ranges=[('factory Setup allocation/registration slice',0x236528,0x2365c4),('service item constructor',0x260ba4,0x260c90),('serviceList getter',0x260c90,0x260c9c),('findItem and inline size/index helpers',0x260d48,0x260e4c),('findService',0x260e4c,0x260eac),('addItem',0x260eac,0x260f04),('CApiBase constructor',0x260f78,0x2610cc),('getId',0x26117c,0x2611e4),('vector end-cap helper',0x261c80,0x261cac),('end-cap identity helpers',0x261ea8,0x261ee0),('getExecutor',0x263130,0x2631ec),('Setup constructor',0x3f0bec,0x3f0d04)]
lines=a.assembly.read_text().splitlines();instructions={}
for line in lines:
 m=re.match(r'\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(.*)',line)
 if m:instructions[int(m[1],16)]=(int(m[2],16).to_bytes(4,'little'),line)
selected=[];counts=[]
for name,start,end in ranges:
 selected.append('; '+name+' ['+hex(start)+','+hex(end)+')')
 for va in range(start,end,4):
  word,line=instructions[va];assert at(va,4)==word;selected.append(line)
 counts.append((name,start,end,(end-start)//4));selected.append('')
a.output.mkdir(parents=True,exist_ok=True);(a.output/'ownership.asm').write_text('\n'.join(selected)+'\n')
result=['schema_version = "mho900-lab.passive-ownership-static/1"','verification = "accepted"','stock_native_sha256 = '+json.dumps(pin),'instructions_checked = '+str(sum(c[3] for c in counts)),'instruction_bytes_match_stock_elf = true','elf_dynamic_symbols_checked = true','elf_relocations_checked = true','physical_contact = false','guest_execution = false','live_owner_discovered = false','bounds_are_proposed_reader_policy = true','proposed_max_services = 64','proposed_max_vector_capacity = 128','ownership_assembly_sha256 = '+json.dumps(hashlib.sha256((a.output/'ownership.asm').read_bytes()).hexdigest())]
for name,start,end,count in counts:result+=['','[[ranges]]','name = '+json.dumps(name),'start = '+json.dumps(hex(start)),'end_exclusive = '+json.dumps(hex(end)),'instructions = '+str(count)]
for name,(va,size) in wanted.items():result+=['','[[symbols]]','name = '+json.dumps(name),'value = '+json.dumps(hex(va)),'size = '+str(size)]
for name,vptr,offset in [('complete Setup',0xb6c3b0,0),('CApiBase subobject',0xb6c3f0,-8),('CSerial subobject',0xb6c418,-72)]:result+=['','[[vtable_address_points]]','name = '+json.dumps(name),'value = '+json.dumps(hex(vptr)),'offset_to_top = '+str(offset),'typeinfo = "0xb6c440"']
(a.output/'ownership-verification.toml').write_text('\n'.join(result)+'\n')
print('ownership instruction words verified:',sum(c[3] for c in counts))
