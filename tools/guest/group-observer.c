/* Thread-aware mapped-read experiment. Stock code/artifacts remain unchanged. */
#define entry native_probe_legacy_entry
#include "native-probe.c"
#undef entry
#include "thread-group.h"
#include "adc-transcript.h"
#include "spu-transcript.h"
struct GmShared {
    unsigned ready,release,worker_go,worker_ack,mapped,hold;
    U worker,new_worker,mapping,output,arm;
    U at_slots[AT_BINDINGS];
    unsigned at_addr[AT_TABLE_WORDS],at_value[AT_TABLE_WORDS],at_source[4];
    unsigned at_shadow9; unsigned short at_shadow8,pad;
    unsigned at_spu[4];
    U st_slots[ST_BINDINGS];
    unsigned st_globals[3],st_series[ST_SERIES][8],st_samples[ST_SAMPLES][4],st_shadows[ST_SHADOWS];
    unsigned st_tables[5][16][4],st_configs[4];
};
_Static_assert(__builtin_offsetof(struct GmShared,st_slots)==1080,"st_slots offset");
_Static_assert(__builtin_offsetof(struct GmShared,st_globals)==1200,"st_globals offset");
_Static_assert(__builtin_offsetof(struct GmShared,st_series)==1212,"st_series offset");
_Static_assert(__builtin_offsetof(struct GmShared,st_samples)==1500,"st_samples offset");
_Static_assert(__builtin_offsetof(struct GmShared,st_shadows)==1548,"st_shadows offset");
_Static_assert(__builtin_offsetof(struct GmShared,st_tables)==1564,"st_tables offset");
_Static_assert(__builtin_offsetof(struct GmShared,st_configs)==2844,"st_configs offset");
_Static_assert(sizeof(struct GmShared)==2864,"shared size");
static struct GmShared *gm;
static unsigned char gm_stack1[16384] __attribute__((aligned(16)));
static unsigned char gm_stack2[16384] __attribute__((aligned(16)));
extern char gm_first_pc[],gm_second_pc[],gm_worker_pc[],gm_store_pc[],gm_stop_pc[],gm_write_pc[],gm_write64_pc[];
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
__attribute__((naked)) static void gm_write(U address __attribute__((unused)),U value __attribute__((unused))) {
    __asm__ volatile("mov x8, x0\nmov x9, x1\n.global gm_write_pc\ngm_write_pc:\nstr w9, [x8]\nret");
}
__attribute__((naked)) static void gm_write64(U address __attribute__((unused)),U value __attribute__((unused))) {
    __asm__ volatile("mov x8, x0\nmov x9, x1\n.global gm_write64_pc\ngm_write64_pc:\nstr x9, [x8]\nret");
}
__attribute__((naked)) static void gm_store(U value __attribute__((unused)),U object __attribute__((unused))) {
    __asm__ volatile("mov x8, x0\nmov x9, x1\n.global gm_store_pc\ngm_store_pc:\nstr x8, [x9]\n.global gm_stop_pc\ngm_stop_pc:\nnop\nret");
}
static unsigned char gm_at_bytes[AT_MAX_BYTES+1];
static struct AtInput gm_at;
static int gm_transcript,gm_spu;
static unsigned char gm_st_bytes[ST_BYTES+1];
static void gm_private_leader(U observer);
static int gm_at_reject(const char *reason,U actual,U expected) {
    event("transcript-input-rejected"); put("reason = \""); put(reason); put("\"\n"); hex("actual",actual); hex("expected",expected); return 0;
}
static int gm_at_load(const char *path,unsigned profile,unsigned required_count) {
    S fd=sys(56,(U)-100,(U)path,0,0,0,0); if(fd<0) return gm_at_reject("open",fd,0);
    U used=0;
    while(used<sizeof(gm_at_bytes)) { S n=sys(63,fd,(U)(gm_at_bytes+used),sizeof(gm_at_bytes)-used,0,0,0); if(n<0) { sys(57,fd,0,0,0,0,0); return gm_at_reject("read",n,0); } if(!n) break; used+=(U)n; }
    sys(57,fd,0,0,0,0,0);
    if(used>AT_MAX_BYTES) return gm_at_reject("oversize",used,AT_MAX_BYTES);
    if(used<AT_FIXED_BYTES) return gm_at_reject("truncated",used,AT_FIXED_BYTES);
    for(unsigned i=0;i<8;i++) if(gm_at_bytes[i]!=(unsigned char)"MHOADCT1"[i]) return gm_at_reject("magic",i,gm_at_bytes[i]);
    unsigned count=at_u32(gm_at_bytes+24),total=at_u32(gm_at_bytes+16),actual_profile=at_u32(gm_at_bytes+20);
    if(at_u32(gm_at_bytes+8)!=1 || at_u32(gm_at_bytes+12)!=64) return gm_at_reject("version",at_u32(gm_at_bytes+8),1);
    if(actual_profile!=profile) return gm_at_reject("profile",actual_profile,profile);
    if(!count || count>AT_FULL_WRITES || count!=required_count) return gm_at_reject("write-count",count,required_count);
    if(total!=AT_FIXED_BYTES+8U*count || total!=used) return gm_at_reject("length",used,AT_FIXED_BYTES+8U*count);
    if(at_u32(gm_at_bytes+28)!=AT_TABLE_WORDS || at_u32(gm_at_bytes+32)!=AT_BINDINGS || at_u32(gm_at_bytes+36)!=AT_SHADOWS || at_u32(gm_at_bytes+40)!=0x3000 || at_u32(gm_at_bytes+44)!=4) return gm_at_reject("shape",0,1);
    for(unsigned i=48;i<64;i++) if(gm_at_bytes[i]) return gm_at_reject("reserved",i,0);
    for(unsigned i=64;i<AT_FIXED_BYTES;i++) if(gm_at_bytes[i]!=at_reference[i]) return gm_at_reject("fixed-data",i,at_reference[i]);
    for(unsigned i=0;i<count;i++) {
        if(at_u32(gm_at_bytes+AT_FIXED_BYTES+8*i)!=at_ref_write_offset(i)) return gm_at_reject("write-offset",i,at_ref_write_offset(i));
        if(at_u32(gm_at_bytes+AT_FIXED_BYTES+8*i+4)!=at_ref_write_value(i)) return gm_at_reject("write-value",i,at_ref_write_value(i));
    }
    gm_at.profile=profile; gm_at.count=count; gm_at.total=total; gm_at.bytes=gm_at_bytes;
    event("transcript-input"); hex("profile",profile); hex("write_count",count); hex("total_size",total); hex("table_count",AT_TABLE_WORDS); hex("binding_count",AT_BINDINGS); hex("shadow_count",AT_SHADOWS); hex("write_offset",0x3000); hex("write_width",4);
    event("transcript-input-accepted"); hex("profile",profile); hex("write_count",count); return 1;
}
static int gm_st_reject(const char *reason,U actual,U expected) { event("spu-input-rejected"); put("reason = \""); put(reason); put("\"\n"); hex("actual",actual); hex("expected",expected); return 0; }
static int gm_st_load(const char *path,unsigned profile) {
    S fd=sys(56,(U)-100,(U)path,0,0,0,0); if(fd<0) return gm_st_reject("open",fd,0); U used=0;
    while(used<sizeof(gm_st_bytes)) { S n=sys(63,fd,(U)(gm_st_bytes+used),sizeof(gm_st_bytes)-used,0,0,0); if(n<0) { sys(57,fd,0,0,0,0,0); return gm_st_reject("read",n,0); } if(!n) break; used+=(U)n; }
    sys(57,fd,0,0,0,0,0); if(used!=ST_BYTES) return gm_st_reject("length",used,ST_BYTES);
    for(unsigned i=0;i<ST_BYTES;i++) if((i<20 || i>=24) && gm_st_bytes[i]!=st_reference[i]) return gm_st_reject("fixed-data",i,st_reference[i]);
    if(st_u32(gm_st_bytes+20)!=profile) return gm_st_reject("profile",st_u32(gm_st_bytes+20),profile);
    event("spu-input"); hex("profile",profile); hex("total_size",ST_BYTES); hex("write_count",ST_WRITES); hex("binding_count",ST_BINDINGS); hex("series_count",ST_SERIES); hex("sample_count",ST_SAMPLES); hex("shadow_count",ST_SHADOWS); hex("repeat_count",2);
    event("spu-input-accepted"); hex("profile",profile); hex("write_count",ST_WRITES); return 1;
}
static void gm_at_private_init(void) {
    for(unsigned i=0;i<AT_TABLE_WORDS;i++) { gm->at_addr[i]=at_u32(at_reference+328+4*i); gm->at_value[i]=at_u32(at_reference+772+4*i); }
    for(unsigned i=0;i<4;i++) gm->at_source[i]=at_u32(at_reference+1216+4*i);
    gm->at_shadow9=0x67216721; gm->at_shadow8=0xb;
    gm->at_slots[0]=(U)gm_private_leader; gm->at_slots[1]=(U)gm_at_private_init; gm->at_slots[2]=(U)gm_write;
    gm->at_slots[3]=(U)gm_store; gm->at_slots[4]=(U)gm_write;
    gm->at_slots[5]=(U)gm->at_addr; gm->at_slots[6]=(U)gm->at_value; gm->at_slots[7]=(U)gm->at_source; gm->at_slots[8]=(U)(gm->at_source+2);
    gm->at_slots[9]=(U)&gm->at_shadow9; gm->at_slots[10]=(U)&gm->at_shadow8;
    if(gm->arm==21) gm->at_slots[4]++;
    if(gm->arm==22) gm->at_shadow9++;
    if(gm->arm==23) gm->at_value[1]++;
    if(gm->arm==24) gm->at_source[1]++;
}
static void gm_st_private_init(void) {
    static const U f[11]={(U)gm_private_leader,(U)gm_first,(U)gm_second,(U)gm_write,(U)gm_write64,(U)gm_store,(U)gm_worker_read,(U)gm_at_private_init,(U)gm_st_private_init,(U)gm_write,(U)gm_write};
    for(unsigned i=0;i<11;i++) gm->st_slots[i]=f[i];
    gm->st_slots[11]=(U)&gm->st_shadows[0]; gm->st_slots[12]=(U)&gm->st_shadows[1]; gm->st_slots[13]=(U)&gm->st_shadows[2]; gm->st_slots[14]=(U)&gm->st_shadows[3];
    for(unsigned i=0;i<3;i++) gm->st_globals[i]=st_u32(st_reference+432+16*i);
    for(unsigned i=0;i<ST_SERIES;i++) for(unsigned j=0;j<8;j++) gm->st_series[i][j]=st_u32(st_reference+488+32*i+4*j);
    for(unsigned i=0;i<ST_SAMPLES;i++) for(unsigned j=0;j<4;j++) gm->st_samples[i][j]=st_u32(st_reference+792+32*i+4*j);
    static const unsigned table_map[9]={0,0,0,1,2,3,4,4,4},config_map[9]={0,0,1,2,3,0,99,99,99};
    for(unsigned i=0;i<ST_SERIES;i++) { gm->st_series[i][2]=(unsigned)(U)gm->st_tables[table_map[i]]; gm->st_series[i][3]=(unsigned)((U)gm->st_tables[table_map[i]]>>32); if(config_map[i]<4) { gm->st_series[i][6]=(unsigned)(U)&gm->st_configs[config_map[i]]; gm->st_series[i][7]=(unsigned)((U)&gm->st_configs[config_map[i]]>>32); } }
    static const unsigned sample_index[3]={0,1,15}; for(unsigned i=0;i<ST_SAMPLES;i++) for(unsigned j=0;j<4;j++) gm->st_tables[0][sample_index[i]][j]=gm->st_samples[i][j];
    for(unsigned i=0;i<ST_SHADOWS;i++) gm->st_shadows[i]=st_u32(st_reference+892+32*i);
    if(gm->arm==32) gm->st_slots[9]++;
    if(gm->arm==33) gm->st_globals[0]++;
    if(gm->arm==34) gm->st_series[2][2]++;
    if(gm->arm==35) gm->st_series[2][4]++;
    if(gm->arm==36) { gm->st_samples[1][1]++; gm->st_tables[0][1][1]++; }
    if(gm->arm==37) gm->st_shadows[0]++;
}
static unsigned gm_st_private_operand(unsigned i) {
    unsigned control=gm->st_shadows[0];
    if(i==0) return control;
    if(i==1 || i==2 || i==4) return control&~1U&~16U;
    if(i==3) return (control&~1U)|16U;
    if(i==5) {
        unsigned mode=gm->st_tables[0][1][1],gain=gm->st_shadows[1],gain_byte=(1U%4U)*85U;
        if(mode==1) return gain_byte*0x01010101U;
        if(mode==2) return (gain&0xffff0000U)|(gain_byte*0x101U);
        return (gain&0xffffff00U)|gain_byte;
    }
    if(i==6) return gm->st_shadows[2]|0x20000000U;
    unsigned vector=0x01010101U,packed=0; for(unsigned j=0;j<4;j++) packed|=((vector>>(8*j))&1U)<<j;
    unsigned mode=gm->st_tables[0][15][1],mask=(mode==1||mode==2)?0:packed;
    return (gm->st_shadows[3]&~0x00f00000U)|(mask<<20)|1U;
}
static void gm_st_private_before_write(unsigned i) {
    unsigned value=gm_st_private_operand(i);
    if(i<5) gm->st_shadows[0]=value; else if(i==5) gm->st_shadows[1]=value; else if(i==6) gm->st_shadows[2]=value; else gm->st_shadows[3]=value;
}
static unsigned gm_load(unsigned *p) { return __atomic_load_n(p,__ATOMIC_ACQUIRE); }
static void gm_publish(unsigned *p) { __atomic_store_n(p,1,__ATOMIC_RELEASE); check(sys(98,(U)p,1,128,0,0,0),"group-wake"); }
static void gm_wait_flag(unsigned *p) {
    while(!gm_load(p)) { S rc=sys(98,(U)p,0,0,0,0,0); if(rc<0 && rc!=-4 && rc!=-11) check(rc,"group-futex-wait"); }
}
static void gm_worker2(void) { gm_wait_flag(&gm->hold); quit(88); }
static void gm_worker1(void) {
    gm_wait_flag(&gm->worker_go); gm_publish(&gm->worker_ack);
    if(gm->arm==2 || gm->arm==4 || gm->arm==6 || gm->arm==10 || gm->arm==14 || gm->arm==26) { gm_wait_flag(&gm->mapped); gm->output=gm_worker_read(gm->mapping+0x4040); quit(88); }
    if(gm->arm==19 || gm->arm==30) { gm_wait_flag(&gm->mapped); gm_write(gm->mapping+(gm->arm==30?st_write_offset(0):at_ref_write_offset(0)),gm->arm==30?st_write_value(0):at_ref_write_value(0)); quit(88); }
    gm_wait_flag(&gm->hold); quit(88);
}
static void gm_private_leader(U observer) {
    check(sys(167,1,9,0,0,0,0),"parent-death-signal"); if(sys(173,0,0,0,0,0,0)!=(S)observer) quit(72);
    if(gm_transcript) gm_at_private_init(); if(gm_spu) gm_st_private_init();
    S worker=gm_clone(0x10f00,(U)(gm_stack1+sizeof(gm_stack1)),gm_worker1); check(worker,"group-existing-worker");
    gm->worker=worker; gm_publish(&gm->ready); gm_wait_flag(&gm->release);
    gm_publish(&gm->worker_go); gm_wait_flag(&gm->worker_ack);
    S next=gm_clone(0x10f00,(U)(gm_stack2+sizeof(gm_stack2)),gm_worker2); check(next,"group-new-worker"); gm->new_worker=next;
    S fd=sys(56,(U)-100,(U)"/dev/null",0x101002,0,0,0); check(fd,"group-control-open");
    U mapping=sys(222,0,0x1000000,3,1,fd,0); gm->mapping=mapping;
    U high=gm_first(mapping+0x4048);
    if(gm->arm==2) { gm_publish(&gm->mapped); gm_wait_flag(&gm->hold); quit(88); }
    U low=gm_second(mapping+(gm->arm==1?0x4040:0x4044));
    gm_store(((high<<32)|low)&0x01ffffffffffffffUL,(U)&gm->output);
    if(gm->arm==3) { gm->output=gm_second(mapping+0x4040); quit(88); }
    if(gm->arm==4) { gm_publish(&gm->mapped); gm_wait_flag(&gm->hold); quit(88); }
    if(gm->arm==5) { gm_write(mapping+0x3000,0x05630000); gm_write(mapping+0x3000,0x01630000); quit(88); }
    if(gm->arm==6) { gm_write(mapping+0x3000,0x05630000); gm_publish(&gm->mapped); gm_wait_flag(&gm->hold); quit(88); }
    if(gm->arm==7) { gm_write(mapping+0x3000,0x05630001); quit(88); }
    if(gm->arm==8) { gm_write(mapping+0x3004,0x05630000); quit(88); }
    if(gm->arm==9) { gm_write(mapping+0x3000,0x05630000); gm_write(mapping+0x3000,0x01630000); gm->output=gm_second(mapping+0x4040); quit(88); }
    if(gm->arm==10) { gm_write(mapping+0x3000,0x05630000); gm_write(mapping+0x3000,0x01630000); gm_publish(&gm->mapped); gm_wait_flag(&gm->hold); quit(88); }
    if(gm->arm==11) { gm_write(mapping+0x3000,0x05630000); gm_write(mapping+0x3000,0x01630001); quit(88); }
    if(gm->arm==12) { gm_write(mapping+0x3000,0x05630000); gm_write(mapping+0x3004,0x01630000); quit(88); }
    if(gm->arm>=13) {
        unsigned limit=(gm->arm==15 || gm->arm==16 || gm->arm==18)?2:AT_FULL_WRITES;
        if(gm->arm==17) { gm_write(mapping+at_ref_write_offset(1),at_ref_write_value(1)); quit(88); }
        if(gm->arm==19) { gm_publish(&gm->mapped); gm_wait_flag(&gm->hold); quit(88); }
        if(gm->arm==20) { gm_write64(mapping+at_ref_write_offset(0),at_ref_write_value(0)); quit(88); }
        for(unsigned i=0;i<limit;i++) {
            U address=mapping+at_ref_write_offset(i); U value=at_ref_write_value(i);
            if(gm->arm==15 && i==1) value++;
            if(gm->arm==16 && i==1) address+=4;
            gm_write(address,value);
        }
        if(limit==AT_FULL_WRITES) { gm->at_shadow9=0x47215721; gm->at_shadow8=0; }
        if(gm_spu) {
            if(gm->arm==29) { gm_write(mapping+st_write_offset(1),st_write_value(1)); quit(88); }
            if(gm->arm==30) { gm_publish(&gm->mapped); gm_wait_flag(&gm->hold); quit(88); }
            if(gm->arm==31) { gm_write64(mapping+st_write_offset(0),st_write_value(0)); quit(88); }
            unsigned slimit=(gm->arm==27 || gm->arm==28)?2:ST_WRITES;
            for(unsigned i=0;i<slimit;i++) { gm_st_private_before_write(i); U address=mapping+st_write_offset(i),value=(i==0&&gm->arm>=32&&gm->arm<=38)?st_write_value(0):gm_st_private_operand(i); if(gm->arm==27 && i==1)value++; if(gm->arm==28 && i==1)address+=4; gm_write(address,value); }
            if(gm->arm==25) { gm_write(mapping+0x4004,1); quit(88); }
            if(gm->arm==26) { gm_publish(&gm->mapped); gm_wait_flag(&gm->hold); quit(88); }
            if(gm->arm==39) { gm_write(mapping+st_write_offset(0),st_write_value(0)); quit(88); }
            gm_wait_flag(&gm->hold); quit(88);
        }
        if(gm->arm==14) { gm_publish(&gm->mapped); gm_wait_flag(&gm->hold); quit(88); }
        if(gm->arm==13) { gm->output=gm_second(mapping+0x4040); quit(88); }
        gm_wait_flag(&gm->hold); quit(88);
    }
    quit(88);
}
static int gm_armed,gm_next,gm_one_write,gm_pair,gm_confirmed[128];
static U gm_base,gm_mapping,gm_target,gm_object,gm_responses,gm_writes,gm_write_offset,gm_write_value,gm_wait_count;
static int gm_private,gm_at_live_checked,gm_st_live_checked;
static U gm_at_private_target(unsigned i) {
    if(i==0) return (U)gm_private_leader; if(i==1) return (U)gm_at_private_init; if(i==2) return (U)gm_write; if(i==3) return (U)gm_store; if(i==4) return (U)gm_write;
    if(i==5) return (U)gm->at_addr; if(i==6) return (U)gm->at_value; if(i==7) return (U)gm->at_source;
    if(i==8) return (U)(gm->at_source+2); if(i==9) return (U)&gm->at_shadow9; return (U)&gm->at_shadow8;
}
static int gm_at_mismatch(const char *kind,U index,U actual,U expected) {
    event("transcript-live-rejected"); put("category = \""); put(kind); put("\"\n"); hex("index",index); hex("actual",actual); hex("expected",expected); return 0;
}
static int gm_at_live(void) {
    for(unsigned i=0;i<AT_BINDINGS;i++) {
        const unsigned char *b=at_reference+64+24*i; U slot=at_u64(b+8),target=at_u64(b+16);
        U actual=gm_private?gm->at_slots[i]:peek(tg_pid,gm_base+slot); U expected=gm_private?gm_at_private_target(i):gm_base+target;
        event("transcript-binding"); hex("index",i); hex("binding_kind",at_u32(b)); hex("slot",slot); hex("expected_target",expected); hex("actual_target",actual); hex("match",actual==expected);
        if(actual!=expected) return gm_at_mismatch("binding",i,actual,expected);
    }
    for(unsigned table=0;table<2;table++) for(unsigned i=0;i<AT_TABLE_WORDS;i++) {
        U object=gm_private?(table?(U)gm->at_value:(U)gm->at_addr):gm_base+at_u64(at_reference+64+24*(5+table)+16);
        unsigned actual=(unsigned)peek(tg_pid,object+4*i),expected=at_u32(at_reference+(table?772:328)+4*i);
        event("transcript-table-word"); hex("table",table); hex("index",i); hex("object",object); hex("expected",expected); hex("actual",actual); hex("match",actual==expected);
        if(actual!=expected) return gm_at_mismatch("table",table*AT_TABLE_WORDS+i,actual,expected);
    }
    static const U source_offsets[4]={0x994740,0x99473c,0x9948e0,0x9948dc};
    for(unsigned i=0;i<4;i++) {
        U object=gm_private?(U)(gm->at_source+i):gm_base+source_offsets[i]; unsigned expected=at_u32(at_reference+1216+4*i),actual=(unsigned)peek(tg_pid,object);
        event("transcript-source-word"); hex("index",i); hex("object",object); hex("expected",expected); hex("actual",actual); hex("match",actual==expected);
        if(actual!=expected) return gm_at_mismatch("source",i,actual,expected);
    }
    for(unsigned i=0;i<2;i++) {
        const unsigned char *s=at_reference+1232+32*i; U slot=at_u64(s),object=gm_private?(i?(U)&gm->at_shadow8:(U)&gm->at_shadow9):gm_base+at_u64(s+8); unsigned width=at_u32(s+16),expected=at_u32(s+20),actual=(unsigned)peek(tg_pid,object); if(width==2) actual&=0xffff;
        event("transcript-shadow"); put("phase = \"initial\"\n"); hex("index",i); hex("slot",slot); hex("object",object); hex("width",width); hex("expected",expected); hex("actual",actual); hex("match",actual==expected);
        if(actual!=expected) return gm_at_mismatch("shadow",i,actual,expected);
    }
    event("transcript-live-state"); hex("valid",1); hex("checked_bindings",AT_BINDINGS); hex("checked_table_words",2*AT_TABLE_WORDS); hex("checked_sources",4); hex("checked_shadows",2); gm_at_live_checked=1; return 1;
}
static U gm_st_private_target(unsigned i) {
    static const U f[11]={(U)gm_private_leader,(U)gm_first,(U)gm_second,(U)gm_write,(U)gm_write64,(U)gm_store,(U)gm_worker_read,(U)gm_at_private_init,(U)gm_st_private_init,(U)gm_write,(U)gm_write};
    if(i<11) return f[i]; return (U)&gm->st_shadows[i-11];
}
static U gm_st_pointer(U link) {
    static const U links[9]={0xb8f808,0xb8f808,0xb8f808,0xb8f908,0xb8fa08,0xb8fb08,0xb8fc08,0xb8fc08,0xb8fc08};
    static const unsigned maps[9]={0,0,0,1,2,3,4,4,4};
    static const U configs[6]={0xb8f40c,0xb8f40c,0xb8f478,0xb8f2c8,0xb8f3a0,0xb8f40c};
    if(!gm_private) return link?gm_base+link:0;
    for(unsigned i=0;i<9;i++) if(link==links[i]) return (U)gm->st_tables[maps[i]];
    for(unsigned i=0;i<6;i++) if(link==configs[i]) { static const unsigned cm[6]={0,0,1,2,3,0}; return (U)&gm->st_configs[cm[i]]; }
    return 0;
}
static int gm_st_bad(const char *category,U pass,U index,U actual,U expected) {
    event("spu-live-rejected"); put("category = \""); put(category); put("\"\n"); hex("pass",pass); hex("index",index); hex("actual",actual); hex("expected",expected); return 0;
}
static int gm_st_live(void) {
    for(unsigned i=0;i<ST_BINDINGS;i++) {
        const unsigned char *b=st_reference+64+24*i; U slot=st_u64(b+8),target=st_u64(b+16);
        U actual=gm_private?gm->st_slots[i]:peek(tg_pid,gm_base+slot),expected=gm_private?gm_st_private_target(i):gm_base+target;
        event("spu-binding"); hex("index",i); hex("binding_kind",st_u32(b)); hex("slot",slot); hex("expected_target",expected); hex("actual_target",actual); hex("match",actual==expected);
        if(actual!=expected) return gm_st_bad("binding",0,i,actual,expected);
    }
    for(unsigned pass=0;pass<2;pass++) {
        for(unsigned i=0;i<3;i++) { const unsigned char *g=st_reference+424+16*i; U address=gm_private?(U)&gm->st_globals[i]:gm_base+st_u64(g); unsigned expected=st_u32(g+8),actual=(unsigned)peek(tg_pid,address);
            event("spu-global"); hex("pass",pass); hex("index",i); hex("address",address); hex("expected",expected); hex("actual",actual); hex("match",actual==expected); if(actual!=expected) return gm_st_bad("global",pass,i,actual,expected); }
        for(unsigned i=0;i<ST_SERIES;i++) { const unsigned char *s=st_reference+488+32*i; U address=gm_private?(U)gm->st_series[i]:gm_base+0xb8f4f0+32*i; unsigned w[8]; for(unsigned j=0;j<8;j++) w[j]=(unsigned)peek(tg_pid,address+4*j);
            U pointer=(U)w[2]|((U)w[3]<<32),config=(U)w[6]|((U)w[7]<<32),ep=gm_st_pointer(st_u64(s+8)),ec=gm_st_pointer(st_u64(s+24));
            int match=w[0]==st_u32(s)&&w[1]==st_u32(s+4)&&pointer==ep&&w[4]==st_u32(s+16)&&w[5]==st_u32(s+20)&&config==ec;
            event("spu-series"); hex("pass",pass); hex("index",i); hex("address",address); hex("key0",w[0]); hex("expected_key0",st_u32(s)); hex("key1",w[1]); hex("expected_key1",st_u32(s+4)); hex("pointer",pointer); hex("expected_pointer",ep); hex("count",w[4]); hex("expected_count",st_u32(s+16)); hex("word20",w[5]); hex("expected_word20",st_u32(s+20)); hex("config_pointer",config); hex("expected_config_pointer",ec); hex("match",match);
            if(!match) { U actual=w[0],expected=st_u32(s); if(actual==expected){actual=w[1];expected=st_u32(s+4);} if(actual==expected){actual=pointer;expected=ep;} if(actual==expected){actual=w[4];expected=st_u32(s+16);} if(actual==expected){actual=w[5];expected=st_u32(s+20);} if(actual==expected){actual=config;expected=ec;} return gm_st_bad("series",pass,i,actual,expected); } }
        static const unsigned sample_index[3]={0,1,15};
        for(unsigned i=0;i<ST_SAMPLES;i++) { const unsigned char *s=st_reference+776+32*i; U address=gm_private?(U)gm->st_tables[0][sample_index[i]]:gm_base+st_u64(s+8); unsigned a[4]; for(unsigned j=0;j<4;j++)a[j]=(unsigned)peek(tg_pid,address+4*j); int match=1; for(unsigned j=0;j<4;j++)if(a[j]!=st_u32(s+16+4*j))match=0;
            event("spu-sample"); hex("pass",pass); hex("ordinal",i); hex("requested_index",st_u32(s)); hex("address",address); hex("w0",a[0]); hex("expected_w0",st_u32(s+16)); hex("mode",a[1]); hex("expected_mode",st_u32(s+20)); hex("w2",a[2]); hex("expected_w2",st_u32(s+24)); hex("w3",a[3]); hex("expected_w3",st_u32(s+28)); hex("match",match); if(!match){ unsigned j=0; while(j<4&&a[j]==st_u32(s+16+4*j))j++; return gm_st_bad("sample",pass,i,a[j],st_u32(s+16+4*j)); } }
        for(unsigned i=0;i<ST_SHADOWS;i++) { const unsigned char *s=st_reference+872+32*i; U slot=st_u64(s),object=gm_private?(U)&gm->st_shadows[i]:gm_base+st_u64(s+8); unsigned expected=st_u32(s+20),actual=(unsigned)peek(tg_pid,object);
            event("spu-shadow"); hex("pass",pass); hex("index",i); hex("slot",slot); hex("object",object); hex("expected_object",gm_private?(U)&gm->st_shadows[i]:gm_base+st_u64(s+8)); hex("expected",expected); hex("actual",actual); hex("match",actual==expected); if(actual!=expected)return gm_st_bad("shadow",pass,i,actual,expected); }
        event("spu-capture"); hex("pass",pass); hex("valid",1);
        if(pass==0 && gm_private && gm->arm==38) { unsigned before=gm->st_globals[0]; gm->st_globals[0]++; event("spu-private-mutation"); put("category = \"global\"\n"); hex("index",0); hex("before",before); hex("after",gm->st_globals[0]); }
    }
    event("spu-live-state"); hex("valid",1); hex("captures",2); gm_st_live_checked=1; return 1;
}
static void gm_resume(struct TgThread *t) {
    if(!t || !t->live || !t->stopped) tg_fail("resume-state",t?t->tid:0);
    U op=t->tid==tg_pid && !gm_armed?24:7;
    S rc=pt(op,t->tid,0,0); if(rc<0) tg_fail("runtime-resume",rc);
    event("runtime-resume"); hex("tid",t->tid); hex("operation",op); t->stopped=0;
}
static S gm_wait(int *status) {
    for(;;) {
        if(gm_transcript && tg_now()>tg_deadline) tg_fail("runtime-deadline",gm_wait_count);
        S tid=sys(260,(U)-1,(U)status,0x40000001,0,0,0);
        if(tid<0) tg_fail("runtime-wait",tid);
        if(!tid) { tg_tick(); continue; }
        if(++gm_wait_count>200000) tg_fail("runtime-event-limit",gm_wait_count);
        event("runtime-wait"); hex("index",gm_wait_count-1); hex("tid",tid); hex("status",*status); return tid;
    }
}
static void gm_at_terminal(void) {
    for(unsigned i=0;i<2;i++) {
        const unsigned char *s=at_reference+1232+32*i; unsigned width=at_u32(s+16); U slot=at_u64(s),object=gm_private?(i?(U)&gm->at_shadow8:(U)&gm->at_shadow9):gm_base+at_u64(s+8);
        unsigned initial=at_u32(s+20),final=at_u32(s+24),expected=gm_writes>=AT_FULL_WRITES?final:initial,actual=(unsigned)peek(tg_pid,object); if(width==2) actual&=0xffff;
        event("transcript-shadow"); put("phase = \"terminal\"\n"); hex("index",i); hex("slot",slot); hex("object",object); hex("width",width); hex("expected",expected); hex("actual",actual); hex("match",actual==expected);
    }
    static const U slots[4]={0xb8d288,0xb8bb48,0xb8d060,0xb8be90},targets[4]={0x3cb44fc,0x3cb44a0,0x3cb44f0,0x3cb44b0};
    for(unsigned i=0;i<4;i++) { U object=gm_private?(U)&gm->at_spu[i]:peek(tg_pid,gm_base+slots[i]),expected=gm_private?(U)&gm->at_spu[i]:gm_base+targets[i]; event("transcript-spu-shadow"); hex("index",i); hex("slot",slots[i]); hex("object",object); hex("expected_object",expected); hex("object_match",object==expected); hex("value",object==expected?((unsigned)peek(tg_pid,object)):0); }
}
static unsigned gm_st_terminal_expected(unsigned i) {
    unsigned n=gm_writes>AT_FULL_WRITES?(unsigned)(gm_writes-AT_FULL_WRITES):0;
    if(i==0) { static const unsigned v[6]={1,0,0,0x10,0,0}; return v[n<6?n:5]; }
    if(i==1) return n>=5?st_u32(st_reference+896+32):st_u32(st_reference+892+32);
    if(i==2) return n>=6?st_u32(st_reference+896+64):st_u32(st_reference+892+64);
    return n>=7?st_u32(st_reference+896+96):st_u32(st_reference+892+96);
}
static void gm_st_terminal(void) {
    for(unsigned i=0;i<ST_SHADOWS;i++) { const unsigned char *s=st_reference+872+32*i; U slot=st_u64(s),expected_object=gm_private?(U)&gm->st_shadows[i]:gm_base+st_u64(s+8); U object=gm_private?gm->st_slots[11+i]:peek(tg_pid,gm_base+slot); unsigned expected=gm_st_terminal_expected(i),actual=object==expected_object?(unsigned)peek(tg_pid,object):0;
        event("spu-terminal-shadow"); hex("index",i); hex("slot",slot); hex("object",object); hex("expected_object",expected_object); hex("object_match",object==expected_object); hex("expected",expected); hex("actual",actual); hex("match",object==expected_object&&actual==expected); }
}
static void gm_registers(const char *kind,U tid,struct Regs *r) {
    event(kind); hex("tid",tid); hex("pc",r->pc); hex("relative_pc",gm_private?0:r->pc-gm_base);
    hex("sp",r->sp); hex("pstate",r->pstate);
    for(int i=0;i<31;i++) { char key[]={'x',(char)('0'+i/10),(char)('0'+i%10),0}; hex(key,r->x[i]); }
}
static void gm_fault(U tid,const char *kind,U signal) {
    U info[16]={0}; check(pt(0x4202,tid,0,(U)info),"group-fault-siginfo"); struct Regs r={0}; registers(tid,&r,0);
    event(kind); hex("tid",tid); hex("signal",signal); hex("si_code",(unsigned)info[1]); hex("address",info[2]);
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
        U signal=(status>>8)&255;
        if(signal==11 || signal==7) gm_fault(tid,"terminal-pending-fault",signal);
        else { event("terminal-pending-signal"); hex("tid",tid); hex("status",status); }
    }
    nps_inventory_for(tg_pid,"terminal",stopping_tid);
    event("terminal-state"); hex("object",gm_object); hex("value",peek(tg_pid,gm_object)); hex("responses",gm_responses);
    if(gm_one_write || gm_pair || gm_transcript) { hex("modeled_writes",gm_writes); hex("write_offset",gm_writes?gm_write_offset:0); hex("write_value",gm_writes?gm_write_value:0); }
    if(gm_private) { hex("worker_ack",gm_load(&gm->worker_ack)); hex("fixture_new_tid",gm->new_worker); }
    if(gm_transcript) gm_at_terminal();
    if(gm_spu) gm_st_terminal();
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
    if(gm_one_write || gm_pair || gm_transcript) { hex("write_pc",private?(U)gm_write_pc:base+0x27043c); hex("write_opcode",0xb9000109); }
    if(gm_transcript) { hex("write64_pc",private?(U)gm_write64_pc:0); hex("write64_opcode",0xf9000109); }
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
        if(signal==11 || (gm_next && signal==7)) {
            gm_fault(tid,"mapped-fault",signal); U info[16]={0}; check(pt(0x4202,tid,0,(U)info),"response-siginfo");
            if(gm_next && gm_responses==2) {
                U offset=info[2]-gm_mapping,write_pc=private?(U)gm_write_pc:base+0x27043c;
                if(gm_spu && gm_writes>=AT_FULL_WRITES) {
                    unsigned index=(unsigned)(gm_writes-AT_FULL_WRITES); int has=index<ST_WRITES;
                    U expected_offset=has?st_write_offset(index):0,expected_value=has?st_write_value(index):0;
                    int candidate=has&&tid==pid&&signal==11&&(unsigned)info[1]==2&&gm_mapping&&offset<0x1000000&&r.x[8]==info[2]&&r.pc==write_pc&&(unsigned)peek(tid,r.pc)==0xb9000109;
                    if(candidate&&!gm_st_live_checked&&!gm_st_live()) {
                        event("spu-write-rejected"); hex("tid",tid); hex("index",index); hex("global_index",gm_writes); put("reason = \"live-state\"\n"); hex("offset",offset); hex("pc",r.pc); hex("actual_value",(unsigned)r.x[9]);
                        event("unsupported-access"); hex("tid",tid); hex("responses",gm_responses); hex("writes",gm_writes); put("classification = \"mapped\"\n"); gm_quiesce(tid); quit(78);
                    }
                    if(candidate&&gm_st_live_checked&&offset==expected_offset&&(unsigned)r.x[9]==expected_value) {
                        struct Regs before=r; r.pc+=4; registers(tid,&r,1); struct Regs after={0}; registers(tid,&after,0);
                        for(int i=0;i<31;i++) if(after.x[i]!=before.x[i]) tg_fail("spu-write-register",i);
                        if(after.pc!=before.pc+4||after.sp!=before.sp||after.pstate!=before.pstate) tg_fail("spu-write-state",0);
                        gm_write_offset=offset; gm_write_value=(unsigned)before.x[9]; gm_writes++;
                        event("modeled-write"); hex("tid",tid); hex("index",gm_writes-1); hex("offset",offset); hex("value",gm_write_value); hex("width",4);
                        event("spu-write"); hex("tid",tid); hex("index",index); hex("global_index",gm_writes-1); hex("pc",before.pc); hex("opcode",0xb9000109); hex("offset",offset); hex("value",gm_write_value); hex("width",4);
                        gm_registers("write-registers",tid,&after); if(index+1==ST_WRITES) { event("spu-complete"); hex("writes",ST_WRITES); hex("total_writes",gm_writes); } gm_resume(t); continue;
                    }
                    int mapped=gm_mapping&&info[2]>=gm_mapping&&info[2]<gm_mapping+0x1000000;
                    event(has?"spu-write-rejected":"spu-boundary");
                    if(has) { const char *reason=tid!=pid?"thread":signal!=11?"signal":(unsigned)info[1]!=2?"si-code":offset!=expected_offset?"offset":r.x[8]!=info[2]?"address-register":r.pc!=write_pc?"pc":(unsigned)peek(tid,r.pc)!=0xb9000109?"opcode":"value"; put("reason = \""); put(reason); put("\"\n"); }
                    hex("tid",tid); hex("index",index); hex("global_index",gm_writes); hex("signal",signal); hex("si_code",(unsigned)info[1]); hex("address",info[2]); hex("offset",offset); hex("pc",r.pc); hex("opcode",(unsigned)peek(tid,r.pc)); hex("actual_value",(unsigned)r.x[9]); hex("expected_offset",expected_offset); hex("expected_value",expected_value); hex("writes",gm_writes);
                    event("unsupported-access"); hex("tid",tid); hex("responses",gm_responses); hex("writes",gm_writes); put("classification = \""); put(mapped?"mapped":"nonmapped"); put("\"\n"); gm_quiesce(tid); quit(mapped?78:83);
                }
                U write_limit=gm_transcript?gm_at.count:(gm_pair?2:1);
                int has_expected=gm_writes<write_limit;
                U expected_offset=gm_transcript?(has_expected?at_u32(gm_at.bytes+AT_FIXED_BYTES+8*gm_writes):0):0x3000;
                U expected_write=gm_transcript?(has_expected?at_u32(gm_at.bytes+AT_FIXED_BYTES+8*gm_writes+4):0):(gm_pair && gm_writes==1?0x01630000:0x05630000);
                if(gm_transcript && !gm_at_live_checked && tid==pid && signal==11 && (unsigned)info[1]==2 && gm_mapping && offset<0x1000000 && r.x[8]==info[2] && r.pc==write_pc && (unsigned)peek(tid,r.pc)==0xb9000109) {
                    if(!gm_at_live()) {
                        event("transcript-write-rejected"); hex("tid",tid); hex("index",gm_writes); put("reason = \"live-state\"\n"); hex("offset",offset); hex("pc",r.pc); hex("actual_value",(unsigned)r.x[9]);
                        event("unsupported-access"); hex("tid",tid); hex("responses",gm_responses); hex("writes",gm_writes); put("classification = \"mapped\"\n"); gm_quiesce(tid); quit(78);
                    }
                }
                if((gm_one_write || gm_pair || gm_transcript) && gm_writes<write_limit && (!gm_transcript || gm_at_live_checked) && tid==pid && signal==11 && (unsigned)info[1]==2 &&
                    gm_mapping && offset==expected_offset && r.x[8]==info[2] && r.pc==write_pc &&
                    (unsigned)peek(tid,r.pc)==0xb9000109 && (unsigned)r.x[9]==expected_write) {
                    struct Regs before=r; r.pc+=4; registers(tid,&r,1); struct Regs after={0}; registers(tid,&after,0);
                    for(int i=0;i<31;i++) if(after.x[i]!=before.x[i]) tg_fail("write-register",i);
                    if(after.pc!=before.pc+4 || after.sp!=before.sp || after.pstate!=before.pstate) tg_fail("write-state",0);
                    gm_write_offset=offset; gm_write_value=(unsigned)before.x[9]; gm_writes++;
                    event("modeled-write"); hex("tid",tid); hex("index",gm_writes-1); hex("offset",gm_write_offset); hex("value",gm_write_value); hex("width",4);
                    if(gm_transcript) { event("transcript-write"); hex("tid",tid); hex("index",gm_writes-1); hex("pc",before.pc); hex("opcode",0xb9000109); hex("offset",gm_write_offset); hex("value",gm_write_value); hex("width",4); }
                    gm_registers("write-registers",tid,&after); if(gm_transcript && gm_writes==gm_at.count) { event("transcript-complete"); hex("writes",gm_writes); } gm_resume(t); continue;
                }
                int mapped=gm_mapping && info[2]>=gm_mapping && info[2]<gm_mapping+0x1000000;
                if(gm_transcript) {
                    event(gm_writes>=write_limit?"transcript-boundary":"transcript-write-rejected");
                    if(gm_writes<write_limit) { const char *reason=tid!=pid?"thread":signal!=11?"signal":(unsigned)info[1]!=2?"si-code":offset!=expected_offset?"offset":r.x[8]!=info[2]?"address-register":r.pc!=write_pc?"pc":(unsigned)peek(tid,r.pc)!=0xb9000109?"opcode":"value"; put("reason = \""); put(reason); put("\"\n"); }
                    hex("tid",tid); hex("index",gm_writes); hex("signal",signal); hex("si_code",(unsigned)info[1]); hex("address",info[2]); hex("offset",offset); hex("pc",r.pc); hex("opcode",(unsigned)peek(tid,r.pc)); hex("actual_value",(unsigned)r.x[9]); hex("expected_offset",has_expected?expected_offset:0); hex("expected_value",has_expected?expected_write:0); hex("writes",gm_writes);
                }
                event("unsupported-access"); hex("tid",tid); hex("responses",gm_responses); hex("writes",gm_writes);
                put("classification = \""); put(mapped?"mapped":"nonmapped"); put("\"\n");
                gm_quiesce(tid); quit(mapped?78:83);
            }
            U expected_pc=private?(gm_responses==0?(U)gm_first_pc:(U)gm_second_pc):base+0x270604;
            U expected_offset=gm_responses==0?0x4048:0x4044;
            if(signal!=11 || tid!=pid || gm_responses>=2 || !gm_mapping || (unsigned)info[1]!=2 || info[2]!=gm_mapping+expected_offset ||
                r.x[8]!=info[2] || r.pc!=expected_pc || (unsigned)peek(tid,r.pc)!=0xb9400109) {
                event("response-guard-rejected"); hex("tid",tid); hex("responses",gm_responses);
                gm_quiesce(tid); quit(78);
            }
            U value=gm_responses==0?0xe1234567:0x89abcdef;
            r.x[9]=value; r.pc+=4; registers(tid,&r,1); struct Regs after={0}; registers(tid,&after,0);
            for(int i=0;i<31;i++) if(after.x[i]!=r.x[i]) tg_fail("response-register",i);
            if(after.pc!=r.pc || after.sp!=r.sp || after.pstate!=r.pstate) tg_fail("response-state",0);
            event("modeled-read"); hex("tid",tid); hex("index",gm_responses); hex("value",value); gm_registers("response-registers",tid,&after);
            if(++gm_responses==2) {
                if(gm_next) {
                    event("continuation-mode"); hex("responses",2); hex("hardware_breakpoint",0); hex("resume_operation",7);
                    gm_armed=1;
                } else { int rc=nps_arm(pid,gm_target); if(rc) tg_fail("hardware-stop-setup",rc); gm_armed=1; }
            }
            gm_resume(t); continue;
        }
        if(signal==5 && gm_armed && !gm_next && tid==pid) {
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
    int spu_control=argc==5&&equal(argv[1],"control-spu"),spu_stock=argc==6&&equal(argv[1],"stock-spu");
    if(spu_control||spu_stock) {
        U arm=spu_control?parse(argv[2],10):0; if(spu_control&&(arm<25||arm>39))quit(2); unsigned profile=spu_stock?1:2;
        if(!gm_at_load(argv[spu_stock?4:3],profile,AT_FULL_WRITES))quit(2);
        if(!gm_st_load(argv[spu_stock?5:4],profile))quit(2);
        gm_transcript=1; gm_spu=1; gm_next=1; tg_deadline=tg_now()+10000;
        if(spu_stock) { U pid=parse(argv[2],10),base=parse(argv[3],16); event("model-mode"); put("scope = \"stock\"\n"); hex("pid",pid); hex("continuation",1); hex("one_write",0); hex("pair_write",0); hex("transcript",1); hex("spu",1); hex("profile",1); hex("write_count",AT_FULL_WRITES); hex("spu_write_count",ST_WRITES); gm_observe(pid,base,0); quit(2); }
        S memory=sys(222,0,32768,3,0x21,(U)-1,0); check(memory,"model-shared-mmap"); gm=(struct GmShared *)memory; gm->arm=arm; gm->output=(U)-1; U observer=sys(172,0,0,0,0,0,0);
        S pid=sys(220,17,0,0,0,0,0); check(pid,"model-private-clone"); if(!pid)gm_private_leader(observer); while(!gm_load(&gm->ready))tg_tick();
        event("model-mode"); put("scope = \"private\"\n"); hex("arm",arm); hex("pid",pid); hex("fixture_worker",gm->worker); hex("continuation",1); hex("one_write",0); hex("pair_write",0); hex("transcript",1); hex("spu",1); hex("profile",2); hex("write_count",AT_FULL_WRITES); hex("spu_write_count",ST_WRITES); gm_observe(pid,0,1); quit(2);
    }
    int transcript_control=argc==4 && equal(argv[1],"control-transcript");
    int transcript_stock=argc==5 && equal(argv[1],"stock-transcript");
    if(transcript_control || transcript_stock) {
        U arm=transcript_control?parse(argv[2],10):0; if(transcript_control && (arm<13 || arm>24)) quit(2);
        unsigned profile=transcript_stock?1:2,required_count=arm==18?1:AT_FULL_WRITES; if(!gm_at_load(argv[transcript_stock?4:3],profile,required_count)) quit(2);
        gm_transcript=1; gm_next=1; tg_deadline=tg_now()+10000;
        if(transcript_stock) {
            U pid=parse(argv[2],10),base=parse(argv[3],16); event("model-mode"); put("scope = \"stock\"\n"); hex("pid",pid); hex("continuation",1); hex("one_write",0); hex("pair_write",0); hex("transcript",1); hex("profile",1); hex("write_count",gm_at.count); gm_observe(pid,base,0); quit(2);
        }
        S memory=sys(222,0,16384,3,0x21,(U)-1,0); check(memory,"model-shared-mmap"); gm=(struct GmShared *)memory;
        gm->arm=arm; gm->output=(U)-1; U observer=sys(172,0,0,0,0,0,0);
        S pid=sys(220,17,0,0,0,0,0); check(pid,"model-private-clone"); if(!pid) gm_private_leader(observer);
        while(!gm_load(&gm->ready)) tg_tick();
        event("model-mode"); put("scope = \"private\"\n"); hex("arm",arm); hex("pid",pid); hex("fixture_worker",gm->worker); hex("continuation",1); hex("one_write",0); hex("pair_write",0); hex("transcript",1); hex("profile",2); hex("write_count",gm_at.count);
        gm_observe(pid,0,1); quit(2);
    }
    if(argc==4 && (equal(argv[1],"stock") || equal(argv[1],"stock-next") || equal(argv[1],"stock-write") || equal(argv[1],"stock-pair-write"))) {
        gm_next=equal(argv[1],"stock-next"); gm_one_write=equal(argv[1],"stock-write"); gm_pair=equal(argv[1],"stock-pair-write"); if(gm_pair) gm_one_write=1; if(gm_one_write) gm_next=1;
        U pid=parse(argv[2],10),base=parse(argv[3],16); event("model-mode"); put("scope = \"stock\"\n"); hex("pid",pid); hex("continuation",gm_next); hex("one_write",gm_one_write&&!gm_pair); hex("pair_write",gm_pair); gm_observe(pid,base,0);
    }
    if(argc!=3 || !equal(argv[1],"control")) quit(2); U arm=parse(argv[2],10); if(arm>12) quit(2); gm_next=arm>=3; gm_one_write=arm>=5; gm_pair=arm>=9;
    tg_deadline=tg_now()+10000; S memory=sys(222,0,4096,3,0x21,(U)-1,0); check(memory,"model-shared-mmap"); gm=(struct GmShared *)memory;
    gm->arm=arm; gm->output=(U)-1; U observer=sys(172,0,0,0,0,0,0);
    S pid=sys(220,17,0,0,0,0,0); check(pid,"model-private-clone"); if(!pid) gm_private_leader(observer);
    while(!gm_load(&gm->ready)) tg_tick();
    event("model-mode"); put("scope = \"private\"\n"); hex("arm",arm); hex("pid",pid); hex("fixture_worker",gm->worker); hex("continuation",gm_next); hex("one_write",gm_one_write&&!gm_pair); hex("pair_write",gm_pair);
    gm_observe(pid,0,1); quit(2);
}
