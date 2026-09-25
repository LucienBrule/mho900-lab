/* Private ARM64 guest observer control. Freestanding native ABI fixture; no stock code. */
typedef unsigned long U;
typedef long S;
struct Regs { U x[31], sp, pc, pstate; };
struct Iov { void *base; U size; };
static volatile unsigned short word=1;
static volatile unsigned attempts[8]={~0U,~0U,~0U,~0U,~0U,~0U,~0U,~0U};
extern char exclusive_loop[], exclusive_terminal[];
static S sys(S n,U a,U b,U c,U d,U e,U f) {
    register U x0 __asm__("x0")=a, x1 __asm__("x1")=b, x2 __asm__("x2")=c;
    register U x3 __asm__("x3")=d, x4 __asm__("x4")=e, x5 __asm__("x5")=f;
    register S x8 __asm__("x8")=n;
    __asm__ volatile("svc 0" : "+r"(x0) : "r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8) : "memory");
    return (S)x0;
}
__attribute__((noreturn)) static void quit(int code) { sys(93,code,0,0,0,0,0); for(;;) {} }
static void put(const char *s) {
    U n=0; while(s[n]) n++;
    if(sys(64,1,(U)s,n,0,0,0)!=(S)n) quit(91);
}
static void hex(const char *name,U value) {
    char t[17]; for(int i=15;i>=0;i--) { t[i]="0123456789abcdef"[value&15]; value>>=4; }
    t[16]=0; put(name); put(" = \"0x"); put(t); put("\"\n");
}
static void event(const char *kind) { put("\n[[events]]\nkind = \""); put(kind); put("\"\n"); }
static void check(S value,const char *operation) {
    if(value<0) { event("error"); put("operation = \""); put(operation); put("\"\n"); hex("result",value); quit(90); }
}
static S pt(U op,U pid,U addr,U data) { return sys(117,op,pid,addr,data,0,0); }
static U peek(U pid,U address) { U data=0; check(pt(2,pid,address,(U)&data),"peek"); return data; }
static void regs(U pid,struct Regs *r) {
    struct Iov io={r,sizeof(*r)}; check(pt(0x4204,pid,1,(U)&io),"getregs");
    if(io.size!=sizeof(*r)) quit(89);
}
static void snapshot(struct Regs *r) {
    hex("pc",r->pc); hex("sp",r->sp); hex("pstate",r->pstate);
    for(int i=0;i<31;i++) { char key[]={'x',(char)('0'+i/10),(char)('0'+i%10),0}; hex(key,r->x[i]); }
}
static void stop_child(U pid) {
    int status=0; check(sys(129,pid,9,0,0,0,0),"kill-child");
    check(sys(260,pid,(U)&status,0x40000000,0,0,0),"reap-child");
    event("terminated"); hex("status",status); if(status!=9) quit(88);
}
__attribute__((noreturn,noinline)) static void child(void) {
    /* Materialize private writable pages before the compared instruction sequence. */
    word=1;
    for(int i=0;i<8;i++) attempts[i]=~0U;
    check(pt(0,0,0,0),"traceme");
    check(sys(129,sys(172,0,0,0,0,0,0),19,0,0,0,0),"initial-stop");
    __asm__ volatile(
        "mov x19, %0\nmov x20, %1\nmov w8, #0\nmov w12, #0\nmov w13, #8\n"
        ".global exclusive_loop\nexclusive_loop:\n"
        "ldxrh w10, [x19]\nstlxrh w11, w8, [x19]\n"
        "str w11, [x20, x12, lsl #2]\nadd w12, w12, #1\n"
        "cbz w11, exclusive_terminal\ncmp w12, w13\nb.lo exclusive_loop\n"
        ".global exclusive_terminal\nexclusive_terminal:\nbrk #0x123\n"
        :: "r"(&word),"r"(attempts) : "x8","x10","x11","x12","x13","x19","x20","cc","memory");
    quit(87);
}
static int equal(const char *a,const char *b) { while(*a && *a==*b) {a++;b++;} return *a==*b; }
void entry(U *stack) {
    U argc=stack[0]; char **argv=(char **)(stack+1);
    if(argc!=2 || (!equal(argv[1],"cont") && !equal(argv[1],"step"))) quit(2);
    int stepped=equal(argv[1],"step");
    put("schema_version = \"mho900-lab.exclusive-control/1\"\n");
    S created=sys(220,17,0,0,0,0,0); check(created,"clone");
    if(!created) child();
    U pid=created; int status=0;
    check(sys(260,pid,(U)&status,0x40000000,0,0,0),"initial-wait");
    if((status&65535)!=(19*256+127)) quit(86);
    check(pt(0x4200,pid,0,0x100000),"exitkill");
    struct Regs r; regs(pid,&r);
    event("setup"); hex("pid",pid); hex("stepped",stepped); hex("clone_flags",17);
    hex("word_address",(U)&word); hex("log_address",(U)attempts);
    hex("loop_pc",(U)exclusive_loop); hex("terminal_pc",(U)exclusive_terminal);
    hex("attempt_limit",8); hex("step_limit",128); hex("initial_word",peek(pid,(U)&word)&65535);
    for(int i=0;i<8;i++) {
        char key[]={'s',(char)('0'+i),0}; hex(key,(unsigned)peek(pid,(U)&attempts[i]));
    }
    event("initial"); snapshot(&r);
    for(U index=0;index<128;index++) {
        if(stepped) { event("instruction"); hex("index",index); hex("pc",r.pc); hex("opcode",(unsigned)peek(pid,r.pc)); }
        check(pt(stepped?9:7,pid,0,0),"resume");
        check(sys(260,pid,(U)&status,0x40000000,0,0,0),"wait");
        if((status&255)!=127) { event("unexpected-exit"); hex("status",status); quit(85); }
        U info[16]={0}; check(pt(0x4202,pid,0,(U)info),"siginfo"); regs(pid,&r);
        event("stop"); hex("index",index); hex("signal",(status>>8)&255);
        hex("si_code",(unsigned)info[1]); hex("address",info[2]); snapshot(&r);
        if(((status>>8)&255)==5 && (unsigned)info[1]==1 && r.pc==(U)exclusive_terminal && info[2]==r.pc &&
            (unsigned)peek(pid,r.pc)==0xd4202460U) {
            event("terminal"); hex("word",peek(pid,(U)&word)&65535);
            hex("attempts",r.x[12]); hex("store_status",r.x[11]); hex("loaded",r.x[10]);
            hex("observer_steps",stepped?index+1:0);
            for(int i=0;i<8;i++) { char key[]={'s',(char)('0'+i),0}; hex(key,(unsigned)peek(pid,(U)&attempts[i])); }
            stop_child(pid); quit(0);
        }
        if(!stepped || ((status>>8)&255)!=5 || (unsigned)info[1]!=4 || info[2]!=r.pc) {
            event("unexpected-stop"); stop_child(pid); quit(84);
        }
    }
    event("step-budget-exhausted"); stop_child(pid); quit(83);
}
__asm__(".global _start\n_start:\nmov x0, sp\nbl entry\n");
