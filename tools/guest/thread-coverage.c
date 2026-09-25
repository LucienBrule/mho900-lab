/* Coverage-only observer and deterministic private discovery controls. No device response. */
#define entry native_probe_legacy_entry
#include "native-probe.c"
#undef entry
#include "thread-group.h"
struct DShared { unsigned ready,spawn,spawned,hold; U existing,late,arm; };
static struct DShared *ds;
static unsigned char dstack1[16384] __attribute__((aligned(16)));
static unsigned char dstack2[16384] __attribute__((aligned(16)));
__attribute__((naked)) static S dclone(U flags __attribute__((unused)),U stack __attribute__((unused)),void (*fn)(void) __attribute__((unused))) {
    __asm__ volatile("mov x9, x2\nmov x2, #0\nmov x3, #0\nmov x4, #0\nmov x8, #220\nsvc #0\n"
        "cbnz x0, 1f\nblr x9\nmov x0, #88\nmov x8, #93\nsvc #0\n1: ret");
}
static unsigned dload(unsigned *p) { return __atomic_load_n(p,__ATOMIC_ACQUIRE); }
static void dpublish(unsigned *p) { __atomic_store_n(p,1,__ATOMIC_RELEASE); check(sys(98,(U)p,1,128,0,0,0),"discovery-wake"); }
static void dwait(unsigned *p) {
    while(!dload(p)) { S rc=sys(98,(U)p,0,0,0,0,0); if(rc<0 && rc!=-4 && rc!=-11) check(rc,"discovery-wait"); }
}
static void late_worker(void) { dwait(&ds->hold); quit(88); }
static void existing_worker(void) {
    if(ds->arm==1) {
        dwait(&ds->spawn);
        S tid=dclone(0x10f00,(U)(dstack2+sizeof(dstack2)),late_worker); check(tid,"late-worker-clone");
        ds->late=tid; dpublish(&ds->spawned);
    }
    dwait(&ds->hold); quit(88);
}
static void after_enumeration(U pass) {
    if(ds->arm!=1 || pass!=0) return;
    dpublish(&ds->spawn); while(!dload(&ds->spawned)) tg_tick();
    event("private-late-thread"); hex("pass",pass); hex("tid",ds->late); hex("creator_tid",ds->existing);
}
void entry(U *stack) {
    U argc=stack[0]; char **argv=(char **)(stack+1); if(argc!=3) quit(2);
    put("schema_version = \"mho900-lab.thread-coverage/1\"\n");
    if(equal(argv[1],"stock")) {
        U pid=parse(argv[2],10); if(pid<2) quit(2);
        event("coverage-mode"); put("scope = \"stock\"\n"); hex("pid",pid);
        tg_discover(pid,0); tg_cleanup(); quit(0);
    }
    if(!equal(argv[1],"control")) quit(2);
    U arm=parse(argv[2],10); if(arm>1) quit(2);
    tg_deadline=tg_now()+10000;
    S memory=sys(222,0,4096,3,0x21,(U)-1,0); check(memory,"discovery-shared-mmap"); ds=(struct DShared *)memory; ds->arm=arm;
    U observer=sys(172,0,0,0,0,0,0);
    S pid=sys(220,17,0,0,0,0,0); check(pid,"discovery-process-clone");
    if(!pid) {
        check(sys(167,1,9,0,0,0,0),"parent-death-signal"); if(sys(173,0,0,0,0,0,0)!=(S)observer) quit(72);
        S tid=dclone(0x10f00,(U)(dstack1+sizeof(dstack1)),existing_worker); check(tid,"existing-worker-clone");
        ds->existing=tid; dpublish(&ds->ready); dwait(&ds->hold); quit(88);
    }
    while(!dload(&ds->ready)) tg_tick();
    event("coverage-mode"); put("scope = \"private\"\n"); hex("arm",arm); hex("pid",pid); hex("fixture_existing_tid",ds->existing);
    tg_discover(pid,after_enumeration); tg_cleanup(); quit(0);
}
