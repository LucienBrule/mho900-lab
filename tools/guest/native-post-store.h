/* Bounded /proc thread inventory and ARM64 hardware-breakpoint observation. */
struct NpsDirent { U ino, off; unsigned short reclen; unsigned char type; char name[]; };
struct NpsDebugSlot { U address; unsigned control, pad; };
struct NpsDebugState { unsigned info, pad; struct NpsDebugSlot slots[16]; };
_Static_assert(sizeof(struct NpsDebugState)==264,"ARM64 hardware debug ABI");

static U nps_append(char *out,U at,U cap,const char *s) {
    while(*s && at+1<cap) out[at++]=*s++;
    out[at]=0; return at;
}
static U nps_decimal(char *out,U at,U cap,U value) {
    char d[24]; U n=0; do { d[n++]=(char)('0'+value%10); value/=10; } while(value);
    while(n && at+1<cap) out[at++]=d[--n]; out[at]=0; return at;
}
static int nps_prefix(const char *s,const char *p) { while(*p && *s==*p) { s++; p++; } return !*p; }
static U nps_number(const char *s) { while(*s==' ' || *s=='\t') s++; return parse(s,10); }
static void nps_status(U pid,U tid,const char *phase) {
    char path[96]="/proc/", data[1024]; U at=6;
    at=nps_decimal(path,at,sizeof(path),pid); at=nps_append(path,at,sizeof(path),"/task/");
    at=nps_decimal(path,at,sizeof(path),tid); nps_append(path,at,sizeof(path),"/status");
    S fd=sys(56,(U)-100,(U)path,0,0,0,0);
    event("thread-status"); put("phase = \""); put(phase); put("\"\n"); hex("tid",tid);
    if(fd<0) { hex("read_error",fd); return; }
    S got=sys(63,fd,(U)data,sizeof(data)-1,0,0,0); sys(57,fd,0,0,0,0,0);
    if(got<0) { hex("read_error",got); return; } data[got]=0;
    U tgid=(U)-1,tracer=(U)-1,state=0; int have_tgid=0,have_tracer=0,have_state=0;
    for(char *line=data;*line;) {
        char *next=line; while(*next && *next!='\n') next++; if(*next) *next++=0;
        if(nps_prefix(line,"Tgid:")) { tgid=nps_number(line+5); have_tgid=1; }
        else if(nps_prefix(line,"TracerPid:")) { tracer=nps_number(line+10); have_tracer=1; }
        else if(nps_prefix(line,"State:")) { char *p=line+6; while(*p==' ' || *p=='\t') p++; state=(unsigned char)*p; have_state=*p!=0; }
        line=next;
    }
    hex("tgid",tgid); hex("tracer_pid",tracer); hex("state",state);
    if(!have_tgid || !have_tracer || !have_state) hex("read_error",1);
}
static void nps_directory_control(U pid) {
    char path[64]="/proc/", buf[2048]; U at=6;
    at=nps_decimal(path,at,sizeof(path),pid); nps_append(path,at,sizeof(path),"/task");
    const U flags[2]={0x10000,0x4000};
    for(int i=0;i<2;i++) {
        S fd=sys(56,(U)-100,(U)path,flags[i],0,0,0), got=0, closed=0;
        if(fd>=0) { got=sys(61,fd,(U)buf,sizeof(buf),0,0,0); closed=sys(57,fd,0,0,0,0,0); }
        event("directory-control"); hex("pid",pid); hex("flags",flags[i]); hex("open_result",fd);
        hex("read_attempted",fd>=0); hex("read_result",got); hex("close_result",closed);
    }
}
static void nps_inventory_for(U pid,const char *phase,U stopping_tid) {
    char path[64]="/proc/", buf[2048]; U at=6, count=0; int overflow=0,error=0;
    U operation=0; S result=0;
    at=nps_decimal(path,at,sizeof(path),pid); nps_append(path,at,sizeof(path),"/task");
    S fd=sys(56,(U)-100,(U)path,0x4000,0,0,0);
    if(fd<0) { error=1; operation=1; result=fd; }
    while(fd>=0 && !overflow && !error) {
        S got=sys(61,fd,(U)buf,sizeof(buf),0,0,0);
        if(got<0) { error=1; operation=2; result=got; break; } if(!got) break;
        for(U pos=0;pos<(U)got;) {
            struct NpsDirent *d=(struct NpsDirent *)(buf+pos);
            if((U)got-pos<20 || d->reclen<20 || pos+d->reclen>(U)got) { error=1; operation=3; result=pos; break; }
            if(d->name[0]>='0' && d->name[0]<='9') {
                U len=0;
                while(19+len<d->reclen && d->name[len]>='0' && d->name[len]<='9') len++;
                if(19+len>=d->reclen || d->name[len]) { error=1; operation=4; result=pos; break; }
                U tid=parse(d->name,10); if(count==128) { overflow=1; break; }
                nps_status(pid,tid,phase); count++;
            }
            pos+=d->reclen;
        }
    }
    if(fd>=0) { S closed=sys(57,fd,0,0,0,0,0); if(closed<0 && !error) { error=1; operation=5; result=closed; } }
    event("thread-inventory"); put("phase = \""); put(phase); put("\"\n");
    hex("pid",pid); hex("observer_pid",sys(172,0,0,0,0,0,0)); hex("stopping_tid",stopping_tid);
    hex("observed_count",count); hex("overflow",overflow); hex("error",error);
    hex("directory_flags",0x4000); hex("error_operation",operation); hex("error_result",result);
}
static void nps_inventory(U pid,const char *phase) { nps_inventory_for(pid,phase,pid); }

static void nps_debug_dump(const char *kind,S rc,struct Iov *io,struct NpsDebugState *s) {
    event(kind); hex("result",rc); hex("size",io->size); hex("info",s->info);
    for(int i=0;i<16;i++) { char a[]={'a',(char)('0'+i/10),(char)('0'+i%10),0}; char c[]={'c',(char)('0'+i/10),(char)('0'+i%10),0}; hex(a,s->slots[i].address); hex(c,s->slots[i].control); }
}
static int nps_arm(U pid,U target) {
    struct NpsDebugState before={0}; struct Iov io={&before,sizeof(before)};
    S rc=pt(0x4204,pid,0x402,(U)&io); nps_debug_dump("debug-before",rc,&io,&before);
    event("debug-profile"); put("guest_profile = \"cached-enable\"\n");
    hex("requested_control",0x1e5); hex("expected_readback_control",0x1e4);
    if(rc<0 || io.size!=sizeof(before) || !(before.info&255)) { event("debug-unsupported"); return 80; }
    for(int i=0;i<16;i++) if(before.slots[i].address || before.slots[i].control) { event("debug-nonempty"); return 81; }
    before.slots[0].address=target; before.slots[0].control=0x1e5; io.size=24;
    nps_debug_dump("debug-request",0,&io,&before); rc=pt(0x4205,pid,0x402,(U)&io);
    event("debug-set"); hex("result",rc); if(rc<0) return 80;
    struct NpsDebugState after={0}; struct Iov aio={&after,sizeof(after)};
    rc=pt(0x4204,pid,0x402,(U)&aio); nps_debug_dump("debug-after",rc,&aio,&after);
    int bad=rc<0 || aio.size!=sizeof(after) || after.info!=before.info || after.slots[0].address!=target || after.slots[0].control!=0x1e4;
    for(int i=1;i<16;i++) if(after.slots[i].address || after.slots[i].control) bad=1;
    if(bad) { event("debug-readback-mismatch"); return 82; }
    return 0;
}
static void nps_terminal(U pid,int child,U base) {
    U target=child?(U)control_pair_stop:base+0x42a8f0;
    int armed=nps_arm(pid,target); if(armed) { terminate_tracee(pid); quit(armed); }
    check(pt(7,pid,0,0),"post-store-continue"); int status=0;
    check(sys(260,pid,(U)&status,0x40000000,0,0,0),"post-store-wait");
    if((status&255)!=127) {
        event("unexpected-exit"); hex("status",status); hex("observer_pid",sys(172,0,0,0,0,0,0));
        hex("stopping_tid",pid); quit(85);
    }
    U info[16]={0}; check(pt(0x4202,pid,0,(U)info),"post-store-siginfo");
    struct Regs r={0}; registers(pid,&r,0);
    int expected=((status>>8)&255)==5 && (unsigned)info[1]==4 && info[2]==r.pc && r.pc==target;
    event("post-store-stop"); hex("status",status); hex("signal",(status>>8)&255); hex("si_code",(unsigned)info[1]); hex("address",info[2]);
    hex("observer_pid",sys(172,0,0,0,0,0,0)); hex("stopping_tid",pid);
    hex("pc",r.pc); hex("relative_pc",child?0:r.pc-base); hex("opcode",expected?(unsigned)peek(pid,r.pc):0);
    for(int i=0;i<31;i++) { char key[]={'x',(char)('0'+i/10),(char)('0'+i%10),0}; hex(key,r.x[i]); }
    if(!expected) { nps_inventory(pid,"terminal"); terminate_tracee(pid); quit(84); }
    U object=child?(U)&control_output:peek(pid,base+0xb8d758), value=peek(pid,object);
    event("post-store-boundary"); hex("expected_stop",expected); hex("target",target); hex("object",object); hex("value",value);
    hex("observer_pid",sys(172,0,0,0,0,0,0)); hex("stopping_tid",pid);
    hex("x8",r.x[8]); hex("x9",r.x[9]); hex("expected_value",0x0123456789abcdefUL);
    nps_inventory(pid,"terminal"); terminate_tracee(pid); quit(0);
}
