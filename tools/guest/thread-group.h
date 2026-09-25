/* Bounded thread-set discovery. Requires the freestanding native-probe ABI helpers. */
struct TgThread { U tid; int live,stopped; };
struct TgIdentity { U tgid,tracer,state; };
static struct TgThread tg_threads[128];
static U tg_count,tg_pid,tg_observer,tg_deadline,tg_wait_count;
static U tg_now(void) {
    U stamp[2]={0}; check(sys(113,1,(U)stamp,0,0,0,0),"group-clock"); return stamp[0]*1000+stamp[1]/1000000;
}
static void tg_fail(const char *reason,S result) {
    event("group-failure"); put("reason = \""); put(reason); put("\"\n"); hex("result",result);
    if(tg_pid) sys(129,tg_pid,9,0,0,0,0); quit(69);
}
static void tg_tick(void) {
    if(tg_now()>tg_deadline) tg_fail("deadline",0);
    U delay[2]={0,1000000}; sys(101,(U)delay,0,0,0,0,0);
}
static struct TgThread *tg_find(U tid) {
    for(U i=0;i<tg_count;i++) if(tg_threads[i].tid==tid) return &tg_threads[i]; return 0;
}
static struct TgThread *tg_add(U tid) {
    struct TgThread *t=tg_find(tid); if(t) { if(!t->live) tg_fail("tid-reuse",tid); return t; }
    if(tg_count==128) tg_fail("thread-limit",tid);
    t=&tg_threads[tg_count++]; t->tid=tid; t->live=1; t->stopped=0;
    event("group-track"); hex("tid",tid); return t;
}
static S tg_identity(U tid,const char *phase,struct TgIdentity *id) {
    char path[80]="/proc/",buf[2048]; U at=nps_decimal(path,6,sizeof(path),tid);
    nps_append(path,at,sizeof(path),"/status"); S fd=sys(56,(U)-100,(U)path,0,0,0,0);
    if(fd<0) return fd;
    S got=sys(63,fd,(U)buf,sizeof(buf)-1,0,0,0); sys(57,fd,0,0,0,0,0);
    if(got<0) return got; buf[got]=0; id->tgid=0; id->tracer=(U)-1; id->state=0;
    for(char *line=buf;*line;) {
        char *next=line; while(*next && *next!='\n') next++; if(*next) *next++=0;
        if(nps_prefix(line,"Tgid:")) id->tgid=nps_number(line+5);
        else if(nps_prefix(line,"TracerPid:")) id->tracer=nps_number(line+10);
        else if(nps_prefix(line,"State:")) { char *p=line+6; while(*p==' ' || *p=='\t') p++; id->state=(unsigned char)*p; }
        line=next;
    }
    event("group-identity"); put("phase = \""); put(phase); put("\"\n");
    hex("tid",tid); hex("tgid",id->tgid); hex("tracer_pid",id->tracer); hex("state",id->state);
    if(id->tgid!=tg_pid || id->tracer==(U)-1 || !id->state) tg_fail("identity",tid);
    return 0;
}
static U tg_enumerate(U pass,U *tids) {
    char path[80]="/proc/",buf[2048]; U at=nps_decimal(path,6,sizeof(path),tg_pid),count=0;
    nps_append(path,at,sizeof(path),"/task"); S fd=sys(56,(U)-100,(U)path,0x4000,0,0,0);
    if(fd<0) tg_fail("directory-open",fd);
    event("enumeration-start"); hex("pass",pass);
    for(;;) {
        S got=sys(61,fd,(U)buf,sizeof(buf),0,0,0); if(got<0) tg_fail("directory-read",got); if(!got) break;
        for(U pos=0;pos<(U)got;) {
            if((U)got-pos<20) tg_fail("directory-short",pos);
            struct NpsDirent *d=(struct NpsDirent *)(buf+pos);
            if(d->reclen<20 || pos+d->reclen>(U)got) tg_fail("directory-record",pos);
            if(d->name[0]>='0' && d->name[0]<='9') {
                U len=0; while(19+len<d->reclen && d->name[len]>='0' && d->name[len]<='9') len++;
                if(19+len>=d->reclen || d->name[len]) tg_fail("directory-name",pos);
                U tid=parse(d->name,10); if(count==128) tg_fail("enumeration-limit",count);
                for(U i=0;i<count;i++) if(tids[i]==tid) tg_fail("duplicate-tid",tid);
                tids[count++]=tid; event("enumerated"); hex("pass",pass); hex("tid",tid);
            }
            pos+=d->reclen;
        }
    }
    S closed=sys(57,fd,0,0,0,0,0); if(closed<0) tg_fail("directory-close",closed);
    event("enumeration-end"); hex("pass",pass); hex("count",count); return count;
}
static int tg_collect(void) {
    int status=0; S tid=sys(260,(U)-1,(U)&status,0x40000001,0,0,0);
    if(tid==0 || tid==-10) return 0; if(tid<0) tg_fail("wait",tid);
    if(++tg_wait_count>256) tg_fail("event-limit",tg_wait_count);
    event("group-wait"); hex("index",tg_wait_count-1); hex("tid",tid); hex("status",status);
    struct TgThread *t=tg_find(tid);
    if((status&255)!=127) {
        if(!t || !t->live) tg_fail("unknown-exit",tid);
        t->live=0; t->stopped=0; event("group-exit"); hex("tid",tid); hex("status",status); return 1;
    }
    if(!t) {
        struct TgIdentity id; S rc=tg_identity(tid,"auto-stop",&id);
        if(rc<0 || id.tracer!=tg_observer) tg_fail("auto-identity",rc);
        t=tg_add(tid);
    }
    if(!t->live || t->stopped) tg_fail("duplicate-stop",tid);
    U kind=(unsigned)status>>16,signal=(status>>8)&255;
    if(signal!=5 || (kind!=128 && kind!=3)) tg_fail("unexpected-stop",status);
    t->stopped=1;
    if(kind==3) {
        U child=0; S rc=pt(0x4201,tid,0,(U)&child); if(rc<0) tg_fail("clone-message",rc);
        event("group-clone"); hex("parent_tid",tid); hex("new_tid",child);
        struct TgIdentity id; rc=tg_identity(child,"clone-child",&id);
        if(rc<0 || id.tracer!=tg_observer) tg_fail("clone-identity",rc);
        tg_add(child);
    }
    return 1;
}
static void tg_discover(U pid,void (*after_enumeration)(U)) {
    tg_pid=pid; tg_observer=sys(172,0,0,0,0,0,0); tg_deadline=tg_now()+10000;
    event("group-setup"); hex("pid",pid); hex("observer_pid",tg_observer); hex("options",0x100008);
    hex("thread_limit",128); hex("pass_limit",16); hex("event_limit",256); hex("deadline_ms",10000);
    for(U pass=0;pass<16;pass++) {
        while(tg_collect()) {}
        U tids[128]; U count=tg_enumerate(pass,tids); if(!count) tg_fail("empty-group",pid);
        if(after_enumeration) after_enumeration(pass);
        int added=0;
        for(U i=0;i<count;i++) {
            struct TgThread *t=tg_find(tids[i]);
            if(t && t->live) continue;
            if(t) tg_fail("listed-exited-tid",tids[i]);
            struct TgIdentity id; S rc=tg_identity(tids[i],"before-seize",&id);
            if(rc==-2 || rc==-3) { event("group-vanished"); hex("tid",tids[i]); hex("result",rc); continue; }
            if(rc<0 || (id.tracer && id.tracer!=tg_observer)) tg_fail("foreign-tracer",rc);
            t=tg_add(tids[i]); added=1;
            if(!id.tracer) {
                rc=pt(0x4206,t->tid,0,0x100008);
                event("group-seize"); hex("tid",t->tid); hex("result",rc); hex("options",0x100008);
                if(rc==-3) { t->live=0; event("group-vanished"); hex("tid",t->tid); hex("result",rc); continue; }
                if(rc<0) {
                    struct TgIdentity after; S identity=tg_identity(t->tid,"seize-race",&after);
                    if(identity<0 || after.tracer!=tg_observer) tg_fail("seize",rc);
                }
            }
            rc=pt(0x4207,t->tid,0,0); event("group-interrupt"); hex("tid",t->tid); hex("result",rc);
            if(rc<0 && rc!=-5) tg_fail("interrupt",rc);
        }
        for(;;) {
            while(tg_collect()) {}
            int pending=0; for(U i=0;i<tg_count;i++) if(tg_threads[i].live && !tg_threads[i].stopped) pending=1;
            if(!pending) break; tg_tick();
        }
        if(added) continue; /* A second enumeration must confirm the now-stopped set. */
        U live=0; for(U i=0;i<tg_count;i++) if(tg_threads[i].live) live++;
        if(live!=count) continue;
        for(U i=0;i<count;i++) {
            struct TgThread *t=tg_find(tids[i]); if(!t || !t->live || !t->stopped) tg_fail("uncovered-tid",tids[i]);
            struct TgIdentity id; S rc=tg_identity(t->tid,"converged",&id);
            if(rc<0 || id.tracer!=tg_observer || id.state!='t') tg_fail("convergence-identity",rc);
        }
        event("group-covered"); hex("pid",pid); hex("observer_pid",tg_observer); hex("count",count); hex("passes",pass+1); return;
    }
    tg_fail("pass-limit",16);
}
static void tg_cleanup(void) {
    U expected=0,count=0; for(U i=0;i<tg_count;i++) if(tg_threads[i].live) expected++;
    S rc=sys(129,tg_pid,9,0,0,0,0); if(rc<0) tg_fail("cleanup-kill",rc);
    for(;;) {
        int status=0; S tid=sys(260,(U)-1,(U)&status,0x40000001,0,0,0);
        if(tid==-10) break; if(tid<0) tg_fail("cleanup-wait",tid); if(!tid) { tg_tick(); continue; }
        struct TgThread *t=tg_find(tid);
        event("group-reaped"); hex("tid",tid); hex("status",status);
        if(!t || !t->live || status!=9) tg_fail("cleanup-identity",tid);
        t->live=0; count++;
    }
    event("group-cleanup"); hex("expected_count",expected); hex("reaped_count",count); hex("wait_result",(U)-10);
    if(expected!=count) tg_fail("cleanup-count",count);
}
