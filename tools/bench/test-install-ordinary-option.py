#!/usr/bin/env python3
"""Host-only actual-module controls; no network connection is initiated."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import threading
import types

p=Path(__file__).with_name('install-ordinary-option.py')
spec=importlib.util.spec_from_file_location('installer',p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
REQUEST=b':SYSTem:OPTion:INSTall MHO-TEST@NONPRODUCTION\n'
DIGEST=hashlib.sha256(REQUEST).hexdigest()
QUERY=b':SYSTem:OPTion:STATus? FLEX\n'

class Clock:
    now=0.
    def monotonic(self):return self.now
    def sleep(self,n):assert n>=0;self.now+=n

class Mock:
    def __init__(self,path,mode):self.path=path;self.mode=mode;self.sent=b'';self.pending=[];self.polls=0;self.calls=0
    def setblocking(self,value):assert value is False
    def send(self,data):
        assert (self.path/'install-request.bin').read_bytes()==REQUEST
        self.calls+=1
        if self.mode=='partial-timeout' and self.sent:raise BlockingIOError()
        if self.mode=='send-error' and self.sent:raise TimeoutError()
        n=min(3,len(data)) if self.mode in ('partial','partial-timeout','send-error') else len(data)
        self.sent+=data[:n]
        if self.sent.endswith(QUERY):
            self.polls+=1
            reply=b'1\n' if self.mode!='zeros' and self.polls>=2 else b'0\n'
            if self.mode=='malformed':reply=b'1\n0\n'
            if self.mode!='response-timeout':self.pending.append(reply)
        return n
    def recv(self,n):
        if not self.pending:raise BlockingIOError()
        return self.pending.pop(0)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);a=parser.parse_args();a.output.mkdir(parents=True)
    originaltime=module.time;passed=[]
    for mode in ('positive','zeros','partial','partial-timeout','send-error','response-timeout','malformed'):
        out=a.output/mode;out.mkdir();module.time=Clock();sock=Mock(out,mode)
        expected_failure=mode in ('partial-timeout','send-error','response-timeout','malformed')
        try:r=module.install(sock,out,REQUEST,DIGEST,'FLEX',lambda:None)
        except module.InstallUncertain as e:
            assert expected_failure;r=e.result
        else:assert not expected_failure
        assert sock.sent[:r['install_bytes_sent']]==REQUEST[:r['install_bytes_sent']]
        if mode in ('partial-timeout','send-error'):assert sock.sent==REQUEST[:3] and sock.polls==0
        else:assert sock.sent==REQUEST+QUERY*sock.polls
        if mode=='zeros':assert not r['observed'] and r['status']=='not-observed' and sock.polls==5
        if mode in ('positive','partial'):assert r['observed'] and sock.polls==2
        if mode in ('response-timeout','malformed'):assert sock.polls==1
        assert module.time.now<=10.021
        assert (out/'result.toml').is_file();passed.append(mode)
    module.time=originaltime
    # Real AF_UNIX stream: async0 then1, no TCP or connect() calls.
    out=a.output/'socketpair';out.mkdir();client,server=socket.socketpair();received=[];errors=[]
    def peer():
        try:
            stream=server.makefile('rb')
            assert stream.readline()==REQUEST;received.append(REQUEST)
            for reply in (b'0\n',b'1\n'):
                assert stream.readline()==QUERY;received.append(QUERY);server.sendall(reply)
        except BaseException as e:errors.append(e)
        finally:server.close()
    worker=threading.Thread(target=peer,daemon=True);worker.start()
    try:r=module.install(client,out,REQUEST,DIGEST,'FLEX',lambda:None)
    finally:client.close()
    worker.join(timeout=2);assert not worker.is_alive() and not errors and r['observed'] and received==[REQUEST,QUERY,QUERY];passed.append('socketpair')
    # Invalid digest and forbidden BND reject before transmission/persistence.
    for name,sha,selector in [('digest','0'*64,'FLEX'),('forbidden-selector',DIGEST,'BND')]:
        out=a.output/name;out.mkdir();sock=Mock(out,name)
        try:module.install(sock,out,REQUEST,sha,selector,lambda:None)
        except ValueError:pass
        else:raise AssertionError(name)
        assert sock.calls==0 and not list(out.iterdir());passed.append(name)
    (a.output/'controls.toml').write_text('schema_version = 1\npassed = true\nphysical_contact = false\ncontrols = '+json.dumps(passed)+'\nsource_sha256 = '+json.dumps(hashlib.sha256(p.read_bytes()).hexdigest())+'\n')
    print('Host installer controls passed: '+str(len(passed)))
if __name__=='__main__':main()
