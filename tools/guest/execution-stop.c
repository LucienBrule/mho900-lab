/* Private post-atomic stop comparison. Shares the exact exclusive-operation child. */
#define entry exclusive_legacy_entry
#include "exclusive-control.c"
#undef entry
#ifndef CACHED_ENABLE_PROFILE
#define CACHED_ENABLE_PROFILE 0
#endif
struct DebugSlot { U address; unsigned control, pad; };
struct DebugState { unsigned info, pad; struct DebugSlot slots[16]; };
_Static_assert(sizeof(struct DebugState)==264,"ARM64 hardware debug ABI");
static void debug_event(const char *kind,S result,struct Iov *io,struct DebugState *state) {
    event(kind); hex("result",result); hex("size",io->size); hex("info",state->info);
    for(int i=0;i<16;i++) {
        char a[]={'a',(char)('0'+i/10),(char)('0'+i%10),0};
        char c[]={'c',(char)('0'+i/10),(char)('0'+i%10),0};
        hex(a,state->slots[i].address); hex(c,state->slots[i].control);
    }
}
void entry(U *stack) {
    U argc=stack[0]; char **argv=(char **)(stack+1);
    if(argc!=2 || (!equal(argv[1],"cont") && !equal(argv[1],"break") && !equal(argv[1],"miss"))) quit(2);
    int use_break=!equal(argv[1],"cont"), miss=equal(argv[1],"miss");
    put("schema_version = \"mho900-lab.execution-stop/1\"\n");
    S created=sys(220,17,0,0,0,0,0); check(created,"clone"); if(!created) child();
    U pid=created; int status=0;
    check(sys(260,pid,(U)&status,0x40000000,0,0,0),"initial-wait");
    if((status&65535)!=(19*256+127)) quit(86);
    check(pt(0x4200,pid,0,0x100000),"exitkill");
    struct Regs r; regs(pid,&r);
    U target=(U)exclusive_terminal+(miss?4:0);
    event("setup"); hex("pid",pid); hex("use_break",use_break); hex("miss",miss);
    hex("cached_enable_profile",CACHED_ENABLE_PROFILE);
    hex("clone_flags",17); hex("word_address",(U)&word); hex("log_address",(U)attempts);
    hex("loop_pc",(U)exclusive_loop); hex("terminal_pc",(U)exclusive_terminal); hex("target_pc",target);
    hex("attempt_limit",8); hex("initial_word",peek(pid,(U)&word)&65535);
    for(int i=0;i<8;i++) { char key[]={'s',(char)('0'+i),0}; hex(key,(unsigned)peek(pid,(U)&attempts[i])); }
    event("initial"); snapshot(&r);
    if(use_break) {
        struct DebugState state={0}; struct Iov io={&state,sizeof(state)};
        S rc=pt(0x4204,pid,0x402,(U)&io); debug_event("debug-before",rc,&io,&state);
        if(rc<0 || io.size!=sizeof(state) || !(state.info&255)) { event("unsupported"); stop_child(pid); quit(80); }
        for(int i=0;i<16;i++) if(state.slots[i].address || state.slots[i].control) {
            event("nonempty-debug-state"); stop_child(pid); quit(81);
        }
        state.slots[0].address=target; state.slots[0].control=0x1e5;
        io.size=24; debug_event("debug-request",0,&io,&state);
        rc=pt(0x4205,pid,0x402,(U)&io); event("debug-set"); hex("result",rc);
        if(rc<0) { event("unsupported"); stop_child(pid); quit(80); }
        struct DebugState after={0}; struct Iov after_io={&after,sizeof(after)};
        rc=pt(0x4204,pid,0x402,(U)&after_io); debug_event("debug-after",rc,&after_io,&after);
        if(rc<0 || after_io.size!=sizeof(after) || after.info!=state.info ||
            after.slots[0].address!=target || after.slots[0].control!=(CACHED_ENABLE_PROFILE?0x1e4U:0x1e5U)) {
            event("debug-readback-mismatch"); stop_child(pid); quit(82);
        }
        for(int i=1;i<16;i++) if(after.slots[i].address || after.slots[i].control) {
            event("debug-readback-mismatch"); stop_child(pid); quit(82);
        }
    }
    check(pt(7,pid,0,0),"continue"); check(sys(260,pid,(U)&status,0x40000000,0,0,0),"wait");
    if((status&255)!=127) { event("unexpected-exit"); hex("status",status); quit(85); }
    U info[16]={0}; check(pt(0x4202,pid,0,(U)info),"siginfo"); regs(pid,&r);
    event("stop"); hex("signal",(status>>8)&255); hex("si_code",(unsigned)info[1]);
    hex("address",info[2]); hex("opcode",(unsigned)peek(pid,r.pc)); snapshot(&r);
    event("terminal"); hex("word",peek(pid,(U)&word)&65535); hex("attempts",r.x[12]);
    hex("store_status",r.x[11]); hex("loaded",r.x[10]);
    for(int i=0;i<8;i++) { char key[]={'s',(char)('0'+i),0}; hex(key,(unsigned)peek(pid,(U)&attempts[i])); }
    int expected=((status>>8)&255)==5 && r.pc==(U)exclusive_terminal && info[2]==r.pc &&
        (unsigned)peek(pid,r.pc)==0xd4202460U && (unsigned)info[1]==(use_break&&!miss?4U:1U);
    event(expected?"expected-stop":"unexpected-stop"); stop_child(pid); quit(expected?0:84);
}
