/* Thread-aware mapped-read experiment. Stock code/artifacts remain unchanged. */
#define entry native_probe_legacy_entry
#include "native-probe.c"
#undef entry
#include "thread-group.h"
struct GmShared { unsigned ready,release,worker_go,worker_ack,mapped,hold; U worker,new_worker,mapping,output,arm; };
static struct GmShared *gm;
static unsigned char gm_stack1[16384] __attribute__((aligned(16)));
static unsigned char gm_stack2[16384] __attribute__((aligned(16)));
extern char gm_first_pc[],gm_second_pc[],gm_worker_pc[],gm_store_pc[],gm_stop_pc[];
__attribute__((naked)) static S gm_clone(U flags __attribute__((unused)),U stack __attribute__((unused)),void (*fn)(void) __attribute__((unused))) {
    __asm__ volatile("mov x9, x2\nmov x2, #0\nmov x3, #0\nmov x4, #0\nmov x8, #220\nsvc #0\ncbnz x0, 1f\nblr x9\nmov x0, #88\nmov x8, #93\nsvc #0\n1: ret");
}
__attribute__((naked)) static U gm_first(U address __attribute__((unused))) {
    __asm__ volatile("mov x8, x0\n.global gm_first_pc\ngm_first_pc:\nldr w9, [x8]\nmov x0, x9\nret");
}
__attribute__((naked)) static U gm_second(U address __attribute__((unused))) {
    __asm__ volatile("mov x8, x0\n.global gm_second_pc\ngm_second_pc:\nldr w9, [x8]\nmov x0, x9\nret");
}
__attribute__((naked)) static U gm_worker_read(U address __attribute__((unused))) {
    __asm__ volatile("mov x8, x0\n.global gm_worker_pc\ngm_worker_pc:\nldr w9, [x8]\nmov x0, x9\nret");
}
__attribute__((naked)) static void gm_store(U value __attribute__((unused)),U object __attribute__((unused))) {
    __asm__ volatile("mov x8, x0\nmov x9, x1\n.global gm_store_pc\ngm_store_pc:\nstr x8, [x9]\n.global gm_stop_pc\ngm_stop_pc:\nnop\nret");
}
static unsigned gm_load(unsigned *p) { return __atomic_load_n(p,__ATOMIC_ACQUIRE); }
static void gm_publish(unsigned *p) { __atomic_store_n(p,1,__ATOMIC_RELEASE); check(sys(98,(U)p,1,128,0,0,0),"group-wake"); }
static void gm_wait_flag(unsigned *p) {
    while(!gm_load(p)) { S rc=sys(98,(U)p,0,0,0,0,0); if(rc<0 && rc!=-4 && rc!=-11) check(rc,"group-futex-wait"); }
}
static void gm_worker2(void) { gm_wait_flag(&gm->hold); quit(88); }
static void gm_worker1(void) {
    gm_wait_flag(&gm->worker_go); gm_publish(&gm->worker_ack);
    if(gm->arm==2) { gm_wait_flag(&gm->mapped); gm->output=gm_worker_read(gm->mapping+0x4040); quit(88); }
    gm_wait_flag(&gm->hold); quit(88);
}
static void gm_private_leader(U observer) {
    check(sys(167,1,9,0,0,0,0),"parent-death-signal"); if(sys(173,0,0,0,0,0,0)!=(S)observer) quit(72);
    S worker=gm_clone(0x10f00,(U)(gm_stack1+sizeof(gm_stack1)),gm_worker1); check(worker,"group-existing-worker");
    gm->worker=worker; gm_publish(&gm->ready); gm_wait_flag(&gm->release);
    gm_publish(&gm->worker_go); gm_wait_flag(&gm->worker_ack);
    S next=gm_clone(0x10f00,(U)(gm_stack2+sizeof(gm_stack2)),gm_worker2); check(next,"group-new-worker"); gm->new_worker=next;
    S fd=sys(56,(U)-100,(U)"/dev/null",0x101002,0,0,0); check(fd,"group-control-open");
    U mapping=sys(222,0,0x1000000,3,1,fd,0); gm->mapping=mapping;
    U high=gm_first(mapping+0x4048);
    if(gm->arm==2) { gm_publish(&gm->mapped); gm_wait_flag(&gm->hold); quit(88); }
    U low=gm_second(mapping+(gm->arm==1?0x4040:0x4044));
    gm_store(((high<<32)|low)&0x01ffffffffffffffUL,(U)&gm->output); quit(88);
}
static int gm_armed,gm_confirmed[128];
static U gm_base,gm_mapping,gm_target,gm_object,gm_responses,gm_wait_count;
static int gm_private;
static void gm_resume(struct TgThread *t) {
    if(!t || !t->live || !t->stopped) tg_fail("resume-state",t?t->tid:0);
    U op=t->tid==tg_pid && !gm_armed?24:7;
    S rc=pt(op,t->tid,0,0); if(rc<0) tg_fail("runtime-resume",rc);
    event("runtime-resume"); hex("tid",t->tid); hex("operation",op); t->stopped=0;
}
static S gm_wait(int *status) {
    for(;;) {
        S tid=sys(260,(U)-1,(U)status,0x40000001,0,0,0);
        if(tid<0) tg_fail("runtime-wait",tid);
        if(!tid) { tg_tick(); continue; }
        if(++gm_wait_count>200000) tg_fail("runtime-event-limit",gm_wait_count);
        event("runtime-wait"); hex("index",gm_wait_count-1); hex("tid",tid); hex("status",*status); return tid;
    }
}
static void gm_registers(const char *kind,U tid,struct Regs *r) {
    event(kind); hex("tid",tid); hex("pc",r->pc); hex("relative_pc",gm_private?0:r->pc-gm_base);
    hex("sp",r->sp); hex("pstate",r->pstate);
    for(int i=0;i<31;i++) { char key[]={'x',(char)('0'+i/10),(char)('0'+i%10),0}; hex(key,r->x[i]); }
}
static void gm_fault(U tid,const char *kind) {
    U info[16]={0}; check(pt(0x4202,tid,0,(U)info),"group-fault-siginfo"); struct Regs r={0}; registers(tid,&r,0);
    event(kind); hex("tid",tid); hex("signal",11); hex("si_code",(unsigned)info[1]); hex("address",info[2]);
    hex("mapping",gm_mapping); hex("offset",info[2]-gm_mapping); hex("opcode",(unsigned)peek(tid,r.pc)); hex("responses",gm_responses);
    gm_registers("fault-registers",tid,&r);
}
/* Returns one for a clone/new-thread/exit event that has been accounted for. */
static int gm_meta(U tid,int status,int quiescing) {
    struct TgThread *t=tg_find(tid);
    if((status&255)!=127) {
        if(!t || !t->live) tg_fail("unknown-runtime-exit",tid);
        t->live=0; t->stopped=0; event("runtime-exit"); hex("tid",tid); hex("status",status);
        if(tid==tg_pid) tg_fail("leader-exit",status); return 1;
    }
    U kind=(unsigned)status>>16,signal=(status>>8)&255;
    if(!t) {
        if(kind!=128 || signal!=5) tg_fail("unknown-runtime-thread",tid);
        struct TgIdentity id; S rc=tg_identity(tid,"runtime-auto",&id); if(rc<0 || id.tracer!=tg_observer) tg_fail("runtime-auto-identity",rc);
        t=tg_add(tid);
    }
    if(!t->live || t->stopped) tg_fail("runtime-duplicate-stop",tid); t->stopped=1;
    if(kind==3 && signal==5) {
        U child=0; S rc=pt(0x4201,tid,0,(U)&child); if(rc<0) tg_fail("runtime-clone-message",rc);
        event("runtime-clone"); hex("parent_tid",tid); hex("new_tid",child);
        struct TgIdentity id; rc=tg_identity(child,"runtime-clone-child",&id);
        if(rc<0 || id.tracer!=tg_observer) tg_fail("runtime-clone-identity",rc);
        struct TgThread *c=tg_add(child); gm_confirmed[c-tg_threads]=1;
        if(!quiescing) { gm_resume(t); if(c->stopped) gm_resume(c); } return 1;
    }
    if(kind==128 && signal==5) {
        event(quiescing?"terminal-interrupt-stop":"runtime-new-stop"); hex("tid",tid); hex("status",status);
        if(!quiescing && gm_confirmed[t-tg_threads]) gm_resume(t); return 1;
    }
    if(kind) tg_fail("runtime-unknown-event",status);
    return 0;
}
static void gm_quiesce(U stopping_tid) {
    event("terminal-quiesce"); hex("stopping_tid",stopping_tid);
    for(U i=0;i<tg_count;i++) if(tg_threads[i].live && !tg_threads[i].stopped) {
        S rc=pt(0x4207,tg_threads[i].tid,0,0); event("terminal-interrupt"); hex("tid",tg_threads[i].tid); hex("result",rc);
        if(rc<0 && rc!=-5) tg_fail("terminal-interrupt",rc);
    }
    for(;;) {
        int pending=0; for(U i=0;i<tg_count;i++) if(tg_threads[i].live && !tg_threads[i].stopped) pending=1;
        if(!pending) break;
        int status=0; U tid=gm_wait(&status); if(gm_meta(tid,status,1)) continue;
        if(((status>>8)&255)==11) gm_fault(tid,"terminal-pending-fault");
        else { event("terminal-pending-signal"); hex("tid",tid); hex("status",status); }
    }
    nps_inventory_for(tg_pid,"terminal",stopping_tid);
    event("terminal-state"); hex("object",gm_object); hex("value",peek(tg_pid,gm_object)); hex("responses",gm_responses);
    if(gm_private) { hex("worker_ack",gm_load(&gm->worker_ack)); hex("fixture_new_tid",gm->new_worker); }
    tg_cleanup();
}
static void gm_observe(U pid,U base,int private) {
    gm_private=private; gm_base=base; gm_target=private?(U)gm_stop_pc:base+0x42a8f0;
    tg_options=0x100009; tg_discover(pid,0);
    for(U i=0;i<tg_count;i++) gm_confirmed[i]=1;
    gm_object=private?(U)&gm->output:peek(pid,base+0xb8d758);
    if(!private && ((unsigned)peek(pid,base+0x270604)!=0xb9400109 || gm_object!=base+0xbbccf0 ||
        (unsigned)peek(pid,base+0x42a8ec)!=0xf9000128 || (unsigned)peek(pid,gm_target)!=0x14000001)) tg_fail("stock-binding",0);
    event("model-binding"); hex("pid",pid); hex("base",base); hex("target",gm_target); hex("object",gm_object); hex("initial_value",peek(pid,gm_object));
    hex("first_pc",private?(U)gm_first_pc:base+0x270604); hex("second_pc",private?(U)gm_second_pc:base+0x270604);
    hex("worker_pc",private?(U)gm_worker_pc:0); hex("store_pc",private?(U)gm_store_pc:base+0x42a8ec);
    hex("target_opcode",(unsigned)peek(pid,gm_target)); hex("store_opcode",(unsigned)peek(pid,private?(U)gm_store_pc:base+0x42a8ec));
    if(!private) { hex("got_slot",base+0xb8d758); hex("mmap_got",peek(pid,base+0xb850f0)); }
    nps_inventory(pid,"before-ready");
    event("ready"); hex("pid",pid); hex("observer_pid",tg_observer); hex("stopping_tid",pid);
    if(private) gm_publish(&gm->release);
    for(U i=0;i<tg_count;i++) if(tg_threads[i].live) gm_resume(&tg_threads[i]);
    U fd=(U)-1; int pending_open=0,pending_map=0;
    for(;;) {
        int status=0; U tid=gm_wait(&status); if(gm_meta(tid,status,0)) continue;
        U signal=(status>>8)&255; struct TgThread *t=tg_find(tid); struct Regs r={0}; registers(tid,&r,0);
        if(signal==11) {
            gm_fault(tid,"mapped-fault"); U info[16]={0}; check(pt(0x4202,tid,0,(U)info),"response-siginfo");
            U expected_pc=private?(gm_responses==0?(U)gm_first_pc:(U)gm_second_pc):base+0x270604;
            U expected_offset=gm_responses==0?0x4048:0x4044;
            if(tid!=pid || gm_responses>=2 || !gm_mapping || (unsigned)info[1]!=2 || info[2]!=gm_mapping+expected_offset ||
                r.x[8]!=info[2] || r.pc!=expected_pc || (unsigned)peek(tid,r.pc)!=0xb9400109) {
                event("response-guard-rejected"); hex("tid",tid); hex("responses",gm_responses);
                gm_quiesce(tid); quit(78);
            }
            U value=gm_responses==0?0xe1234567:0x89abcdef;
            r.x[9]=value; r.pc+=4; registers(tid,&r,1); struct Regs after={0}; registers(tid,&after,0);
            for(int i=0;i<31;i++) if(after.x[i]!=r.x[i]) tg_fail("response-register",i);
            if(after.pc!=r.pc || after.sp!=r.sp || after.pstate!=r.pstate) tg_fail("response-state",0);
            event("modeled-read"); hex("tid",tid); hex("index",gm_responses); hex("value",value); gm_registers("response-registers",tid,&after);
            if(++gm_responses==2) { int rc=nps_arm(pid,gm_target); if(rc) tg_fail("hardware-stop-setup",rc); gm_armed=1; }
            gm_resume(t); continue;
        }
        if(signal==5 && gm_armed && tid==pid) {
            U info[16]={0}; check(pt(0x4202,tid,0,(U)info),"terminal-siginfo");
            event("post-store-stop"); hex("tid",tid); hex("status",status); hex("signal",signal); hex("si_code",(unsigned)info[1]); hex("address",info[2]);
            hex("opcode",(unsigned)peek(tid,r.pc)); gm_registers("post-store-registers",tid,&r);
            if((unsigned)info[1]!=4 || info[2]!=gm_target || r.pc!=gm_target) tg_fail("terminal-stop",0);
            event("post-store-boundary"); hex("target",gm_target); hex("object",gm_object); hex("value",peek(pid,gm_object)); hex("x8",r.x[8]); hex("x9",r.x[9]);
            gm_quiesce(tid); quit(0);
        }
        if(signal!=133 || tid!=pid || gm_armed) {
            event("unexpected-runtime-signal"); hex("tid",tid); hex("status",status); gm_registers("unexpected-registers",tid,&r);
            gm_quiesce(tid); quit(83);
        }
        event("runtime-syscall"); hex("tid",tid); hex("phase",r.x[7]); hex("number",r.x[8]);
        hex("pc",r.pc); hex("lr",r.x[30]);
        for(int i=0;i<6;i++) { char key[]={'a',(char)('0'+i),0}; hex(key,r.x[i]); }
        if(r.x[7]==0) {
            pending_open=0; pending_map=0;
            if(r.x[8]==56) {
                char path[64]; remote_string(pid,r.x[1],path,sizeof(path));
                if(equal(path,private?"/dev/null":"/dev/xdma0_bypass") && r.x[2]==0x101002) pending_open=1;
            }
            if(r.x[8]==222 && fd!=(U)-1 && r.x[4]==fd) {
                event("mmap-request"); for(int i=0;i<6;i++) { char key[]={'a',(char)('0'+i),0}; hex(key,r.x[i]); } hex("pc",r.pc); hex("lr",r.x[30]);
                if(r.x[0] || r.x[1]!=0x1000000 || r.x[2]!=3 || r.x[3]!=1 || r.x[5] || gm_mapping || (!private && r.x[30]!=base+0x270284)) tg_fail("mmap-guard",0);
                r.x[2]=0; r.x[3]=0x22; r.x[4]=(U)-1; registers(pid,&r,1); pending_map=1;
            }
        } else if(r.x[7]==1) {
            if(pending_open) { pending_open=0; if((S)r.x[0]>=0) { fd=r.x[0]; event("open-result"); hex("fd",fd); } }
            if(pending_map) { pending_map=0; gm_mapping=r.x[0]; event("mapping-result"); hex("base",gm_mapping); hex("protection",0); if((S)gm_mapping<0 || !gm_mapping) tg_fail("mapping-result",gm_mapping); }
        } else tg_fail("syscall-phase",r.x[7]);
        gm_resume(t);
    }
}
void entry(U *stack) {
    U argc=stack[0]; char **argv=(char **)(stack+1);
    put("schema_version = \"mho900-lab.group-observer/1\"\n");
    if(argc==4 && equal(argv[1],"stock")) {
        U pid=parse(argv[2],10),base=parse(argv[3],16); event("model-mode"); put("scope = \"stock\"\n"); hex("pid",pid); gm_observe(pid,base,0);
    }
    if(argc!=3 || !equal(argv[1],"control")) quit(2); U arm=parse(argv[2],10); if(arm>2) quit(2);
    tg_deadline=tg_now()+10000; S memory=sys(222,0,4096,3,0x21,(U)-1,0); check(memory,"model-shared-mmap"); gm=(struct GmShared *)memory;
    gm->arm=arm; gm->output=(U)-1; U observer=sys(172,0,0,0,0,0,0);
    S pid=sys(220,17,0,0,0,0,0); check(pid,"model-private-clone"); if(!pid) gm_private_leader(observer);
    while(!gm_load(&gm->ready)) tg_tick();
    event("model-mode"); put("scope = \"private\"\n"); hex("arm",arm); hex("pid",pid); hex("fixture_worker",gm->worker);
    gm_observe(pid,0,1); quit(2);
}
