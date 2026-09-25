/* Private shared-mapping thread coverage controls. Reuses the native guest ABI only. */
#define entry native_probe_legacy_entry
#include "native-probe.c"
#undef entry
struct TcShared {
    unsigned ready, release, completed, hold;
    U existing_tid, new_tid, mapping, result, arm;
};
static struct TcShared *tc;
static U tc_deadline;
static unsigned char tc_stack1[16384] __attribute__((aligned(16)));
static unsigned char tc_stack2[16384] __attribute__((aligned(16)));
extern char tc_first_pc[],tc_second_pc[],tc_write_pc[];
__attribute__((naked)) static U tc_first(U address __attribute__((unused))) {
    __asm__ volatile("mov x8, x0\n.global tc_first_pc\ntc_first_pc:\nldr w9, [x8]\nmov x0, x9\nret");
}
__attribute__((naked)) static U tc_second(U address __attribute__((unused))) {
    __asm__ volatile("mov x8, x0\n.global tc_second_pc\ntc_second_pc:\nldr w9, [x8]\nmov x0, x9\nret");
}
__attribute__((naked)) static void tc_write(U address __attribute__((unused))) {
    __asm__ volatile("mov x8, x0\nmov w9, #0x55\n.global tc_write_pc\ntc_write_pc:\nstr w9, [x8]\nret");
}
/* No TLS or parent/child TID pointers are used. Child switches to a distinct aligned stack. */
__attribute__((naked)) static S tc_clone(U flags __attribute__((unused)),U stack __attribute__((unused)),
    void (*fn)(void) __attribute__((unused))) {
    __asm__ volatile("mov x9, x2\nmov x2, #0\nmov x3, #0\nmov x4, #0\nmov x8, #220\nsvc #0\n"
        "cbnz x0, 1f\nblr x9\nmov x0, #88\nmov x8, #93\nsvc #0\n1: ret");
}
static unsigned tc_load(unsigned *p) { return __atomic_load_n(p,__ATOMIC_ACQUIRE); }
static void tc_publish(unsigned *p,unsigned value) {
    __atomic_store_n(p,value,__ATOMIC_RELEASE); check(sys(98,(U)p,1,128,0,0,0),"futex-wake");
}
static void tc_wait(unsigned *p,unsigned value) {
    while(tc_load(p)!=value) {
        unsigned observed=tc_load(p); if(observed==value) break;
        S rc=sys(98,(U)p,0,observed,0,0,0); if(rc<0 && rc!=-4 && rc!=-11) check(rc,"futex-wait");
    }
}
static void tc_worker1(void) {
    tc_wait(&tc->release,1);
    tc->result=tc_first(tc->mapping+(tc->arm==1?0x4040:0x4048));
    tc_publish(&tc->completed,1); tc_wait(&tc->hold,1); quit(88);
}
static void tc_worker2(void) {
    if(tc->arm==2) tc_write(tc->mapping+0x4044);
    else tc->result=tc_second(tc->mapping+0x4044);
    quit(88);
}
static U tc_now(void) {
    U stamp[2]={0}; check(sys(113,1,(U)stamp,0,0,0,0),"clock-monotonic"); return stamp[0]*1000+stamp[1]/1000000;
}
static void tc_tick(void) {
    if(tc_now()>tc_deadline) { event("deadline"); quit(70); }
    U delay[2]={0,1000000}; sys(101,(U)delay,0,0,0,0,0);
}
static S tc_waitpid(S pid,int *status,int allow_empty) {
    for(;;) {
        S rc=sys(260,pid,(U)status,0x40000001,0,0,0);
        if(rc!=0 || allow_empty) return rc;
        tc_tick();
    }
}
static void tc_regs(const char *kind,U tid,struct Regs *r) {
    event(kind); hex("tid",tid); hex("pc",r->pc); hex("sp",r->sp); hex("pstate",r->pstate);
    for(int i=0;i<31;i++) { char key[]={'x',(char)('0'+i/10),(char)('0'+i%10),0}; hex(key,r->x[i]); }
}
static void tc_cleanup(U pid,U expected) {
    check(sys(129,pid,9,0,0,0,0),"kill-private-group"); U count=0;
    for(;;) {
        int status=0; S tid=tc_waitpid(-1,&status,0);
        if(tid==-10) break;
        check(tid,"reap-private-thread");
        event("reaped"); hex("tid",tid); hex("status",status);
        if((status&127)!=9 || ++count>3) quit(71);
    }
    event("cleanup"); hex("reaped_count",count); hex("expected_count",expected); hex("wait_result",(U)-10);
    if(count!=expected) quit(71); quit(0);
}
void entry(U *stack) {
    U argc=stack[0]; char **argv=(char **)(stack+1);
    if(argc!=2) quit(2); U arm=parse(argv[1],10); if(arm>2) quit(2);
    put("schema_version = \"mho900-lab.thread-control/1\"\n");
    tc_deadline=tc_now()+10000;
    S memory=sys(222,0,4096,3,0x21,(U)-1,0); check(memory,"shared-control-mmap"); tc=(struct TcShared *)memory;
    S mapped=sys(222,0,0x1000000,0,0x22,(U)-1,0); check(mapped,"private-device-mmap");
    tc->mapping=mapped; tc->arm=arm; tc->result=(U)-1;
    U observer=sys(172,0,0,0,0,0,0);
    S pid=sys(220,17,0,0,0,0,0); check(pid,"private-process-clone");
    if(!pid) {
        check(sys(167,1,9,0,0,0,0),"parent-death-signal");
        if(sys(173,0,0,0,0,0,0)!=(S)observer) quit(72);
        S worker=tc_clone(0x10f00,(U)(tc_stack1+sizeof(tc_stack1)),tc_worker1); check(worker,"existing-worker-clone");
        tc->existing_tid=worker; tc_publish(&tc->ready,1);
        tc_wait(&tc->completed,1);
        S next=tc_clone(0x10f00,(U)(tc_stack2+sizeof(tc_stack2)),tc_worker2); check(next,"new-worker-clone");
        tc->new_tid=next; tc_wait(&tc->hold,1); quit(88);
    }
    while(!tc_load(&tc->ready)) tc_tick();
    U tids[3]={(U)pid,tc->existing_tid,0};
    event("setup"); hex("arm",arm); hex("observer_pid",observer); hex("pid",pid); hex("existing_tid",tids[1]);
    hex("mapping",mapped); hex("mapping_length",0x1000000); hex("first_pc",(U)tc_first_pc);
    hex("second_pc",(U)tc_second_pc); hex("write_pc",(U)tc_write_pc); hex("clone_flags",0x10f00);
    for(int i=0;i<2;i++) {
        S rc=pt(0x4206,tids[i],0,0x100008);
        event("seize"); hex("tid",tids[i]); hex("options",0x100008); hex("result",rc); check(rc,"seize-existing");
        check(pt(0x4207,tids[i],0,0),"interrupt-existing");
    }
    for(int i=0;i<2;i++) {
        int status=0; check(tc_waitpid(tids[i],&status,0),"initial-thread-wait");
        event("initial-stop"); hex("tid",tids[i]); hex("status",status);
        if(status!=0x80057f) quit(73);
        nps_status(pid,tids[i],"initial");
    }
    nps_inventory(pid,"covered");
    event("release"); hex("covered_threads",2); tc_publish(&tc->release,1);
    for(int i=0;i<2;i++) check(pt(7,tids[i],0,0),"continue-existing");
    U responses=0,pending_tid=0; int new_started=0;
    for(U index=0;index<32;index++) {
        int status=0; S tid=tc_waitpid(-1,&status,0); check(tid,"thread-event-wait");
        event("wait"); hex("index",index); hex("tid",tid); hex("status",status);
        if((status&255)!=127) quit(74);
        U kind=(unsigned)status>>16,signal=(status>>8)&255;
        if(kind==3 && (U)tid==tids[0] && signal==5 && responses==1 && !tids[2]) {
            U new_tid=0; check(pt(0x4201,tid,0,(U)&new_tid),"clone-event-message");
            if(!new_tid || new_tid==tids[0] || new_tid==tids[1]) quit(75); tids[2]=new_tid;
            if(pending_tid && pending_tid!=new_tid) quit(75);
            unsigned completed=tc_load(&tc->completed);
            event("clone"); hex("parent_tid",tid); hex("new_tid",new_tid); hex("shared_result",tc->result); hex("completed",completed);
            check(pt(7,tid,0,0),"continue-cloning-thread");
            if(pending_tid) { new_started=1; check(pt(7,pending_tid,0,0),"continue-pending-new-thread"); }
            continue;
        }
        if(kind==128 && signal==5 && responses==1 && !new_started && !pending_tid &&
            (U)tid!=tids[0] && (U)tid!=tids[1] && (!tids[2] || (U)tid==tids[2])) {
            pending_tid=tid; event("new-thread-stop"); hex("tid",tid); hex("status",status);
            nps_status(pid,tid,"new-thread");
            if(tids[2]) { new_started=1; check(pt(7,tid,0,0),"continue-new-thread"); }
            continue;
        }
        if(kind || signal!=11 || ((U)tid!=tids[1] && (U)tid!=tids[2])) { event("unexpected-thread-event"); quit(76); }
        U info[16]={0}; check(pt(0x4202,tid,0,(U)info),"thread-siginfo"); struct Regs r={0}; registers(tid,&r,0);
        U opcode=(unsigned)peek(tid,r.pc);
        event("mapped-fault"); hex("tid",tid); hex("signal",signal); hex("si_code",(unsigned)info[1]);
        hex("address",info[2]); hex("offset",info[2]-tc->mapping); hex("opcode",opcode); hex("responses",responses);
        tc_regs("fault-registers",tid,&r);
        if((unsigned)info[1]!=2 || info[2]!=r.x[8] || info[2]<tc->mapping || info[2]>=tc->mapping+0x1000000) quit(77);
        if((U)tid==tids[1] && responses==0 && r.pc==(U)tc_first_pc && opcode==0xb9400109 && info[2]==tc->mapping+0x4048) {
            r.x[9]=0x11223344; r.pc+=4; registers(tid,&r,1); struct Regs actual={0}; registers(tid,&actual,0);
            tc_regs("response-registers",tid,&actual); responses++;
            check(pt(7,tid,0,0),"continue-modeled-private-read"); continue;
        }
        unsigned completed=tc_load(&tc->completed);
        event("terminal"); hex("tid",tid); hex("responses",responses); hex("new_started",new_started);
        hex("shared_result",tc->result); hex("completed",completed);
        nps_inventory_for(pid,"terminal",tid); tc_cleanup(pid,tids[2]?3:2);
    }
    event("event-budget"); quit(78);
}
