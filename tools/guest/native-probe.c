/* ARM64 Linux 3.18 research supervisor. No libc, app injection or instruction patching.
 * Native ABI exception: ptrace and freestanding guest execution; Kotlin verifies evidence.
 */
typedef unsigned long U;
typedef long S;
struct Regs { U x[31], sp, pc, pstate; };
struct Iov { void *base; U size; };
static S sys(S n, U a, U b, U c, U d, U e, U f) {
    register U x0 __asm__("x0")=a, x1 __asm__("x1")=b, x2 __asm__("x2")=c;
    register U x3 __asm__("x3")=d, x4 __asm__("x4")=e, x5 __asm__("x5")=f;
    register S x8 __asm__("x8")=n;
    __asm__ volatile("svc 0" : "+r"(x0) : "r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8) : "memory");
    return (S)x0;
}
__attribute__((noreturn)) static void quit(int code) { sys(93,code,0,0,0,0,0); for (;;) {} }
static U length(const char *s) { U n=0; while(s[n]) n++; return n; }
static void put(const char *s) {
    U n=length(s); if(sys(64,1,(U)s,n,0,0,0)!=(S)n) quit(91);
}
static void hex(const char *name,U value) {
    char text[17]; for(int i=15;i>=0;i--) { text[i]="0123456789abcdef"[value&15]; value>>=4; }
    text[16]=0; put(name); put(" = \"0x"); put(text); put("\"\n");
}
static void event(const char *kind) { put("\n[[events]]\nkind = \""); put(kind); put("\"\n"); }
static void check(S result,const char *where) {
    if(result<0) { event("error"); put("operation = \""); put(where); put("\"\n"); hex("result",result); quit(90); }
}
static S pt(U op,U pid,U addr,U data) { return sys(117,op,pid,addr,data,0,0); }
static U peek(U pid,U address) { U word=0; check(pt(2,pid,address,(U)&word),"peek"); return word; }
static U parse(const char *s,int radix) {
    U v=0; if(radix==16 && s[0]=='0' && s[1]=='x') s+=2;
    if(!*s) quit(2);
    for(;*s;s++) { U d=*s>='a' ? *s-'a'+10 : *s-'0'; if(d>=(U)radix) quit(2); v=v*radix+d; }
    return v;
}
static void remote_string(U pid,U address,char *out,U capacity) {
    for(U i=0;i+8<=capacity;i+=8) {
        U word=peek(pid,address+i);
        for(U j=0;j<8;j++) { out[i+j]=(char)(word>>(j*8)); if(!out[i+j]) return; }
    }
    out[capacity-1]=0;
}
static int equal(const char *a,const char *b) { while(*a && *a==*b) {a++;b++;} return *a==*b; }
static void registers(U pid,struct Regs *r,int write) {
    struct Iov io={r,sizeof(*r)};
    check(pt(write?0x4205:0x4204,pid,1,(U)&io),write?"setregs":"getregs");
    if(io.size!=sizeof(*r)) quit(89);
}
static void control(U which) {
    check(pt(0,0,0,0),"traceme");
    check(sys(129,sys(172,0,0,0,0,0,0),19,0,0,0,0),"stop");
    S fd=sys(56,(U)-100,(U)"/dev/null",0x101002,0,0,0); check(fd,"control-open");
    U base=sys(222,0,0x1000000,3,1,fd,0);
    /* One known instruction per child; the supervisor never completes it. */
    U address=base+0x4048, value=0x1122334455667788UL;
    switch(which) {
        case 0: __asm__ volatile("ldr w9, [%0]" :: "r"(address) : "x9","memory"); break;
        case 1: __asm__ volatile("str %w0, [%1]" :: "r"(value),"r"(address) : "memory"); break;
        case 2: __asm__ volatile("ldr x9, [%0]" :: "r"(address) : "x9","memory"); break;
        case 3: __asm__ volatile("str %0, [%1]" :: "r"(value),"r"(address) : "memory"); break;
        default: quit(2);
    }
    quit(88); /* Reaching this means the guard failed. */
}
static void supervise(U pid,int child,U base) {
    int status=0;
    if(!child) check(pt(16,pid,0,0),"attach");
    check(sys(260,pid,(U)&status,0x40000000,0,0,0),"initial-wait");
    if((status&255)!=127) quit(87);
    check(pt(0x4200,pid,0,0x100001),"options"); /* TRACESYSGOOD | EXITKILL */
    if(!child) {
        if((unsigned)peek(pid,base+0x270604)!=0xb9400109U ||
           (unsigned)peek(pid,base+0x27043c)!=0xb9000109U) quit(86);
        event("stock-binding"); hex("base",base); hex("mmap_got",peek(pid,base+0xb850f0));
    }
    event("ready"); hex("pid",pid);
    U fd=(U)-1, mapped=0; int pending_open=0,pending_map=0;
    for(U stops=0;stops<200000;stops++) {
        check(pt(24,pid,0,0),"resume");
        check(sys(260,pid,(U)&status,0x40000000,0,0,0),"wait");
        if((status&255)!=127) { event("unexpected-exit"); hex("status",status); quit(85); }
        int sig=(status>>8)&255;
        struct Regs r; registers(pid,&r,0);
        if(sig==11) {
            U info[16]={0}; check(pt(0x4202,pid,0,(U)info),"siginfo");
            U address=info[2], opcode=peek(pid,r.pc)&0xffffffffUL;
            event("fault"); hex("signal",sig); hex("si_code",(unsigned)(info[1]&0xffffffffUL));
            hex("address",address); hex("mapping",mapped); hex("offset",address-mapped);
            hex("pc",r.pc); hex("relative_pc",r.pc-base); hex("opcode",opcode);
            hex("sp",r.sp); hex("pstate",r.pstate);
            for(int i=0;i<31;i++) { char key[]={'x',(char)('0'+i/10),(char)('0'+i%10),0}; hex(key,r.x[i]); }
            check(pt(17,pid,0,11),"detach-fault");
            if(child) check(sys(260,pid,(U)&status,0,0,0,0),"reap-control");
            quit(mapped && address>=mapped && address<mapped+0x1000000 ? 0 : 84);
        }
        if(sig!=133) {
            event("unexpected-signal"); hex("signal",sig);
            check(pt(17,pid,0,sig),"detach-signal"); quit(83);
        }
        /* Linux ARM64 reports entry=0 / exit=1 in temporary x7 at syscall stops. */
        if(r.x[7]==0) {
            pending_open=0; pending_map=0;
            if(r.x[8]==56) {
                char path[64]; remote_string(pid,r.x[1],path,sizeof(path));
                if(equal(path,child?"/dev/null":"/dev/xdma0_bypass") && r.x[2]==0x101002) pending_open=1;
            }
            if(r.x[8]==222 && fd!=(U)-1 && r.x[4]==fd) {
                event("mmap-request");
                for(int i=0;i<6;i++) { char key[]={'a',(char)('0'+i),0}; hex(key,r.x[i]); }
                hex("pc",r.pc); hex("lr",r.x[30]);
                if(r.x[0] || r.x[1]!=0x1000000 || r.x[2]!=3 || r.x[3]!=1 || r.x[5] || mapped ||
                   (!child && r.x[30]!=base+0x270284)) { event("guard-rejected"); pt(17,pid,0,0); quit(82); }
                r.x[2]=0; r.x[3]=0x22; r.x[4]=(U)-1;
                registers(pid,&r,1); pending_map=1;
            }
        } else if(r.x[7]==1) {
            if(pending_open) {
                pending_open=0;
                if((S)r.x[0]>=0) { fd=r.x[0]; event("open-result"); hex("fd",fd); }
            }
            if(pending_map) {
                pending_map=0; mapped=r.x[0];
                event("mapping-result"); hex("base",mapped); hex("protection",0);
                if((S)mapped<0 || !mapped) { pt(17,pid,0,0); quit(81); }
            }
        } else { event("invalid-phase"); hex("x7",r.x[7]); pt(17,pid,0,0); quit(80); }
    }
    pt(17,pid,0,0); quit(79);
}
void entry(U *stack) {
    U argc=stack[0]; char **argv=(char **)(stack+1);
    put("schema_version = \"mho900-lab.native-probe/1\"\n");
    if(argc==3 && equal(argv[1],"control")) {
        U which=parse(argv[2],10); if(which>3) quit(2);
        S pid=sys(220,17,0,0,0,0,0); check(pid,"clone");
        if(!pid) control(which); else supervise(pid,1,0);
    } else if(argc==4 && equal(argv[1],"stock")) supervise(parse(argv[2],10),0,parse(argv[3],16));
    quit(2);
}
__asm__(".global _start\n_start:\nmov x0, sp\nbl entry\n");
