/* Thread-aware mapped-read experiment. Stock code/artifacts remain unchanged. */
#define entry native_probe_legacy_entry
#include "native-probe.c"
#undef entry
#include "thread-group.h"
#include "adc-transcript.h"
#include "spu-transcript.h"
#include "remaining-init.h"
#include "init-tail.h"
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
    unsigned ri_scu,ri_la; int ri_cached; unsigned ri_bool,ri_atomic,ri_device_io,ri_old_executed; U ri_slots[RI_BINDINGS];
    unsigned it_dac,it_control,it_config,it_status,it_packed,it_hw; U it_taps[6]; unsigned it_ready,it_atomic,it_calibration,it_old; U it_slots[IT_BINDINGS];
};
_Static_assert(__builtin_offsetof(struct GmShared,st_slots)==1080,"st_slots offset");
_Static_assert(__builtin_offsetof(struct GmShared,st_globals)==1200,"st_globals offset");
_Static_assert(__builtin_offsetof(struct GmShared,st_series)==1212,"st_series offset");
_Static_assert(__builtin_offsetof(struct GmShared,st_samples)==1500,"st_samples offset");
_Static_assert(__builtin_offsetof(struct GmShared,st_shadows)==1548,"st_shadows offset");
_Static_assert(__builtin_offsetof(struct GmShared,st_tables)==1564,"st_tables offset");
_Static_assert(__builtin_offsetof(struct GmShared,st_configs)==2844,"st_configs offset");
_Static_assert(__builtin_offsetof(struct GmShared,ri_scu)==2860,"ri_scu offset");
_Static_assert(__builtin_offsetof(struct GmShared,ri_la)==2864,"ri_la offset");
_Static_assert(__builtin_offsetof(struct GmShared,ri_cached)==2868,"ri_cached offset");
_Static_assert(__builtin_offsetof(struct GmShared,ri_slots)==2888,"ri_slots offset");
_Static_assert(__builtin_offsetof(struct GmShared,it_dac)==2984,"it_dac offset");
_Static_assert(__builtin_offsetof(struct GmShared,it_taps)==3008,"it_taps offset");
_Static_assert(__builtin_offsetof(struct GmShared,it_slots)==3072,"it_slots offset");
_Static_assert(sizeof(struct GmShared)==3200,"tail shared size");
static struct GmShared *gm;
static unsigned char gm_stack1[16384] __attribute__((aligned(16)));
static unsigned char gm_stack2[16384] __attribute__((aligned(16)));
extern char gm_first_pc[],gm_second_pc[],gm_worker_pc[],gm_read64_pc[],gm_store_pc[],gm_stop_pc[],gm_write_pc[],gm_write64_pc[];
extern char gm_ri_cp0[],gm_ri_cp1[],gm_ri_cp2[],gm_ri_cp3[],gm_ri_cp4[],gm_ri_cp5[],gm_ri_cp6[],gm_ri_cp7[],gm_ri_cp8[],gm_ri_cp9[];
extern char gm_it_cp0[],gm_it_cp1[],gm_it_cp2[];
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
__attribute__((naked)) static U gm_read64(U address __attribute__((unused))) {
    __asm__ volatile("mov x8, x0\n.global gm_read64_pc\ngm_read64_pc:\nldr x9, [x8]\nmov x0, x9\nret");
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
#define RI_CP(n) __attribute__((naked)) static U gm_ri_site##n(U a __attribute__((unused)),U b __attribute__((unused))) { __asm__ volatile(".global gm_ri_cp" #n "\ngm_ri_cp" #n ":\nnop\nret"); }
RI_CP(0) RI_CP(1) RI_CP(2) RI_CP(3) RI_CP(4) RI_CP(5) RI_CP(6) RI_CP(7) RI_CP(8) RI_CP(9)
#define IT_CP(n) __attribute__((naked)) static U gm_it_site##n(U a __attribute__((unused)),U b __attribute__((unused))) { __asm__ volatile(".global gm_it_cp" #n "\ngm_it_cp" #n ":\nnop\nret"); }
IT_CP(0) IT_CP(1) IT_CP(2)
static unsigned char gm_at_bytes[AT_MAX_BYTES+1];
static struct AtInput gm_at;
static int gm_transcript,gm_spu,gm_remaining,gm_tail;
static const char gm_ri_tty[]="/dev/ttyS0",gm_ri_gpio[]="/dev/hdcode_gpio",gm_ri_command[]="*RST\n";
static void gm_ri_atomic_step(void) { __atomic_fetch_add(&gm->ri_atomic,1,__ATOMIC_SEQ_CST); }
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
static void gm_publish(unsigned *p);
static void gm_wait_flag(unsigned *p);
static void gm_tail_private(U mapping);
static void gm_remaining_private(U mapping) {
    gm->ri_scu=0; gm->ri_la=0; gm->ri_cached=-1; gm->ri_bool=0;
    gm->ri_slots[0]=(U)&gm->ri_scu; gm->ri_slots[1]=(U)gm_remaining_private; gm->ri_slots[2]=(U)gm_write;
    gm->ri_slots[3]=(U)gm_ri_cp0; gm->ri_slots[4]=(U)gm_ri_cp0; gm->ri_slots[5]=(U)&gm->ri_cached;
    gm->ri_slots[6]=(U)gm_ri_cp8; gm->ri_slots[7]=(U)gm_ri_cp3; gm->ri_slots[8]=(U)gm_ri_cp4;
    gm->ri_slots[9]=(U)gm_ri_cp9; gm->ri_slots[10]=(U)gm_write; gm->ri_slots[11]=(U)gm_write;
    if(gm->arm==45) gm->ri_slots[9]++;
    if(gm->arm==46) gm->ri_scu=1;
    if(gm->arm==49) { gm_publish(&gm->mapped); gm_wait_flag(&gm->hold); quit(88); }
    if(gm->arm==50) { gm->ri_scu=0x80000000U; gm_write(mapping+0x4004,0); quit(88); }
    gm->ri_scu|=0x80000000U;
    if(gm->arm==45||gm->arm==46) gm_write(mapping+0x4004,0x80000000U);
    else if(gm->arm==47) gm_write(mapping+0x4004,gm->ri_scu+1);
    else if(gm->arm==48) gm_write64(mapping+0x4004,gm->ri_scu);
    else gm_write(mapping+0x4004,gm->ri_scu);
    gm->ri_scu&=0x7ffffffbU; gm_write(mapping+0x4004,gm->ri_scu);
    if(gm->arm==52) { gm_wait_flag(&gm->hold); quit(88); }
    gm_ri_site0((U)gm_ri_tty,1); gm_ri_atomic_step();
    if(gm->arm==53) { gm_ri_site0((U)gm_ri_tty,1); gm->ri_old_executed=1; }
    S board=gm->arm==41?0:-1; gm_ri_site1((U)board,0); gm_ri_atomic_step();
    if(gm->arm==41) gm->ri_device_io=1;
    gm->ri_bool=gm->arm==44; gm_ri_site2((U)-1,gm->ri_bool); gm_ri_atomic_step();
    gm->ri_cached=gm->arm==43?0:-1; gm_ri_site3((U)gm_ri_command,5); gm_ri_atomic_step();
    if(gm->arm!=51) { gm_ri_site4((U)gm_ri_gpio,0x802); gm_ri_atomic_step(); }
    S gpio=gm->arm==42?0:-1; gm_ri_site5((U)gpio,0); gm_ri_atomic_step();
    if(gm->arm==42) gm->ri_device_io=1;
    gm_ri_site6((U)(gm->arm==58?-2:-3),0); gm_ri_atomic_step();
    gm_ri_site7((U)-7,0); gm_ri_atomic_step(); gm->ri_cached=-7;
    gm_ri_site8((U)-3,0); gm_ri_atomic_step();
    if(gm->arm==54) gm->ri_la=2; gm_ri_site9((U)-1,0); gm_ri_atomic_step();
    if(gm->arm==57) { gm_publish(&gm->mapped); gm_wait_flag(&gm->hold); quit(88); }
    gm->ri_la=(gm->ri_la&0xfffffffeU)|1;
    if(gm->arm==55) gm_write(mapping+0x7034,gm->ri_la+1);
    else if(gm->arm==56) gm_write64(mapping+0x7034,gm->ri_la);
    else gm_write(mapping+0x7034,gm->ri_la);
    gm->ri_la&=0xfffffffeU; gm_write(mapping+0x7034,gm->ri_la);
    if(gm_tail) gm_tail_private(mapping);
    gm->output=gm_second(mapping+4); quit(88);
}
static void gm_tail_private(U mapping) {
    gm->it_dac=gm->arm==64?0x10000U:0; gm->it_control=gm->arm==65?1U:0; gm->it_config=gm->arm==66?0U:1U; gm->st_configs[1]=gm->it_config; gm->it_status=0;
    U targets[IT_BINDINGS]={(U)gm_tail_private,(U)gm_tail_private,(U)gm_write,(U)gm_tail_private,(U)gm_tail_private,(U)gm_tail_private,(U)gm_write,(U)gm_tail_private,(U)gm_tail_private,(U)gm_tail_private,(U)gm_tail_private,(U)gm_first,(U)gm_tail_private,(U)&gm->it_control,(U)&gm->it_status,(U)&gm->it_dac};
    for(unsigned i=0;i<IT_BINDINGS;i++)gm->it_slots[i]=targets[i]; if(gm->arm==67)gm->it_slots[0]++;
    if(gm->arm==62) { gm_publish(&gm->mapped); gm_wait_flag(&gm->hold); quit(88); }
    U r0=gm->arm==60?gm_first(mapping):gm->arm==61?gm_read64(mapping+4):gm_first(mapping+4);
    U r1=gm_first(mapping),r2=gm_first(mapping+0x401c);
    gm->it_dac=(gm->it_dac&0xffff0000U)|0x646eU; gm_write(mapping+0x1428,gm->arm==63?0x646f:gm->it_dac);
    gm->it_packed=((unsigned)r0&0xffffffU)<<8|((unsigned)r1&255U); gm->it_hw=(unsigned)r2; if(gm->arm==68)gm->it_packed++;
    if(gm->arm==74){gm->it_config=0;gm->st_configs[1]=0;} __atomic_add_fetch(&gm->it_atomic,1,__ATOMIC_SEQ_CST); gm_it_site0(0,0);
    if(gm->arm==72) { gm_it_site0(0,0); gm->it_old=1; }
    if(gm->arm==73) { gm_publish(&gm->mapped); gm_wait_flag(&gm->hold); quit(88); }
    U a=gm_first(mapping+0x14a0),b=gm_first(mapping+0x14a4),c=gm_first(mapping+0x1498),d=gm_first(mapping+0x14ac),e=gm_first(mapping+0x14b4);
    gm->it_taps[0]=(unsigned)a&0x3f; gm->it_taps[1]=(unsigned)c&0xfff; gm->it_taps[2]=(unsigned)b&0xfff; gm->it_taps[3]=(unsigned)d&0xfff; gm->it_taps[4]=(unsigned)e&0x3ff; gm->it_taps[5]=0;
    gm->it_control&=0xfffffff3U; gm_write(mapping+0x1000,gm->it_control);
    gm->it_status=(unsigned)gm_first(mapping+0x1008); (void)gm_first(mapping+0x1210); gm->it_ready=(gm->it_status>>29)&1U;
    if(gm->arm==69)gm->it_taps[1]^=1UL<<32; if(gm->arm==70)gm->it_ready=0; __atomic_add_fetch(&gm->it_atomic,1,__ATOMIC_SEQ_CST); gm_it_site1(0,0);
    if(gm->arm==71)gm_first(mapping+0x1008);
    __atomic_add_fetch(&gm->it_atomic,1,__ATOMIC_SEQ_CST); gm_it_site2(0,0); gm->it_calibration++; quit(88);
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
    if(gm->arm==19 || gm->arm==30 || gm->arm==49 || gm->arm==57) { gm_wait_flag(&gm->mapped); U off=gm->arm==57?0x7034:gm->arm==49?0x4004:gm->arm==30?st_write_offset(0):at_ref_write_offset(0); U value=gm->arm==57?1:gm->arm==49?0x80000000:gm->arm==30?st_write_value(0):at_ref_write_value(0); gm_write(gm->mapping+off,value); quit(88); }
    if(gm->arm==62) { gm_wait_flag(&gm->mapped); gm_worker_read(gm->mapping+4); quit(88); }
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
            if(gm_remaining) gm_remaining_private(mapping);
            gm_wait_flag(&gm->hold); quit(88);
        }
        if(gm->arm==14) { gm_publish(&gm->mapped); gm_wait_flag(&gm->hold); quit(88); }
        if(gm->arm==13) { gm->output=gm_second(mapping+0x4040); quit(88); }
        gm_wait_flag(&gm->hold); quit(88);
    }
    quit(88);
}
static int gm_armed,gm_next,gm_one_write,gm_pair,gm_confirmed[128];
static unsigned gm_ri_checkpoint,gm_ri_writes;
static unsigned gm_it_checkpoint,gm_it_reads,gm_it_writes;
static U gm_base,gm_mapping,gm_target,gm_object,gm_responses,gm_writes,gm_write_offset,gm_write_value,gm_wait_count;
static int gm_private,gm_at_live_checked,gm_st_live_checked; static U gm_region_clone;
static void gm_quiesce(U stopping_tid);
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
        if(gm_transcript && tg_now()>tg_deadline) { if(gm_remaining) return 0; tg_fail("runtime-deadline",gm_wait_count); }
        S tid=sys(260,(U)-1,(U)status,0x40000001,0,0,0);
        if(tid<0) tg_fail("runtime-wait",tid);
        if(!tid) { if(gm_remaining) { U delay[2]={0,1000000}; sys(101,(U)delay,0,0,0,0,0); } else tg_tick(); continue; }
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
static U gm_ri_private_pc(unsigned i) { static const U p[RI_CHECKPOINTS]={(U)gm_ri_cp0,(U)gm_ri_cp1,(U)gm_ri_cp2,(U)gm_ri_cp3,(U)gm_ri_cp4,(U)gm_ri_cp5,(U)gm_ri_cp6,(U)gm_ri_cp7,(U)gm_ri_cp8,(U)gm_ri_cp9}; return p[i]; }
static U gm_it_private_pc(unsigned i) { static const U p[IT_CHECKPOINTS]={(U)gm_it_cp0,(U)gm_it_cp1,(U)gm_it_cp2}; return p[i]; }
static int gm_regs_same(struct Regs *a,struct Regs *b);
static U gm_ri_private_target(unsigned i) {
    if(i==0)return (U)&gm->ri_scu; if(i==1)return (U)gm_remaining_private; if(i==2||i==10||i==11)return (U)gm_write;
    if(i==3||i==4)return (U)gm_ri_cp0; if(i==5)return (U)&gm->ri_cached; if(i==6)return (U)gm_ri_cp8;
    if(i==7)return (U)gm_ri_cp3; if(i==8)return (U)gm_ri_cp4; return (U)gm_ri_cp9;
}
static int gm_ri_debug(U tid,int next) {
    struct NpsDebugState before={0}; struct Iov io={&before,sizeof(before)}; S rc=pt(0x4204,tid,0x402,(U)&io); nps_debug_dump("remaining-debug-before",rc,&io,&before);
    if(rc<0||io.size!=sizeof(before)||before.info!=0x0606)return 0;
    if(gm_ri_checkpoint==0) { for(int i=0;i<16;i++)if(before.slots[i].address||before.slots[i].control)return 0; }
    else if(before.slots[0].address!=(gm_private?gm_ri_private_pc(gm_ri_checkpoint-1):gm_base+ri_stock_pc[gm_ri_checkpoint-1])||before.slots[0].control!=0x1e4)return 0;
    for(int i=1;i<16;i++)if(before.slots[i].address||before.slots[i].control)return 0;
    before.slots[0].address=0; before.slots[0].control=0; io.size=24; nps_debug_dump("remaining-debug-clear-request",0,&io,&before); rc=pt(0x4205,tid,0x402,(U)&io); event("remaining-debug-clear-set"); hex("result",rc); if(rc<0)return 0;
    struct NpsDebugState clear={0}; struct Iov cio={&clear,sizeof(clear)}; rc=pt(0x4204,tid,0x402,(U)&cio); nps_debug_dump("remaining-debug-clear-after",rc,&cio,&clear); if(rc<0||cio.size!=sizeof(clear)||clear.info!=before.info||clear.slots[0].address||clear.slots[0].control!=(gm_ri_checkpoint?0x1e5U:0x1e4U))return 0; for(int i=1;i<16;i++)if(clear.slots[i].address||clear.slots[i].control)return 0;
    if(!next)return 1; U target=gm_private?gm_ri_private_pc(gm_ri_checkpoint):gm_base+ri_stock_pc[gm_ri_checkpoint]; clear.slots[0].address=target; clear.slots[0].control=0x1e5; cio.size=24; nps_debug_dump("remaining-debug-arm-request",0,&cio,&clear); rc=pt(0x4205,tid,0x402,(U)&cio); event("remaining-debug-arm-set"); hex("result",rc); if(rc<0)return 0;
    struct NpsDebugState after={0}; struct Iov aio={&after,sizeof(after)}; rc=pt(0x4204,tid,0x402,(U)&aio); nps_debug_dump("remaining-debug-arm-after",rc,&aio,&after); if(rc<0||aio.size!=sizeof(after)||after.info!=before.info||after.slots[0].address!=target||after.slots[0].control!=0x1e4)return 0; for(int i=1;i<16;i++)if(after.slots[i].address||after.slots[i].control)return 0;
    event("remaining-debug-ready"); hex("checkpoint",gm_ri_checkpoint); hex("tid",tid); hex("target",target); hex("opcode",(unsigned)peek(tid,target)); return 1;
}
static int gm_it_debug(U tid,int next) {
    struct NpsDebugState before={0}; struct Iov io={&before,sizeof(before)}; S rc=pt(0x4204,tid,0x402,(U)&io); nps_debug_dump("tail-debug-before",rc,&io,&before);
    if(rc<0||io.size!=sizeof(before)||before.info!=0x0606)return 0;
    if(!gm_it_checkpoint) {
        if(before.slots[0].address||before.slots[0].control!=0x1e5U)return 0;
        for(int i=1;i<16;i++)if(before.slots[i].address||before.slots[i].control)return 0;
        if(!next)return 1;
        U target=gm_private?gm_it_private_pc(0):gm_base+it_stock_pc[0];before.slots[0].address=target;before.slots[0].control=0x1e5;io.size=24;nps_debug_dump("tail-debug-arm-request",0,&io,&before);rc=pt(0x4205,tid,0x402,(U)&io);event("tail-debug-arm-set");hex("result",rc);if(rc<0)return 0;
        struct NpsDebugState after={0};struct Iov aio={&after,sizeof(after)};rc=pt(0x4204,tid,0x402,(U)&aio);nps_debug_dump("tail-debug-arm-after",rc,&aio,&after);if(rc<0||aio.size!=sizeof(after)||after.info!=before.info||after.slots[0].address!=target||after.slots[0].control!=0x1e4U)return 0;for(int i=1;i<16;i++)if(after.slots[i].address||after.slots[i].control)return 0;
        event("tail-debug-ready");hex("checkpoint",0);hex("tid",tid);hex("target",target);hex("opcode",(unsigned)peek(tid,target));return 1;
    }
    else if(before.slots[0].address!=(gm_private?gm_it_private_pc(gm_it_checkpoint-1):gm_base+it_stock_pc[gm_it_checkpoint-1])||before.slots[0].control!=0x1e4U)return 0;
    for(int i=1;i<16;i++)if(before.slots[i].address||before.slots[i].control)return 0;
    before.slots[0].address=0;before.slots[0].control=0;io.size=24;nps_debug_dump("tail-debug-clear-request",0,&io,&before);rc=pt(0x4205,tid,0x402,(U)&io);event("tail-debug-clear-set");hex("result",rc);if(rc<0)return 0;
    struct NpsDebugState clear={0};struct Iov cio={&clear,sizeof(clear)};rc=pt(0x4204,tid,0x402,(U)&cio);nps_debug_dump("tail-debug-clear-after",rc,&cio,&clear);if(rc<0||cio.size!=sizeof(clear)||clear.info!=before.info||clear.slots[0].address||clear.slots[0].control!=(gm_it_checkpoint?0x1e5U:0x1e4U))return 0;for(int i=1;i<16;i++)if(clear.slots[i].address||clear.slots[i].control)return 0;
    if(!next)return 1;U target=gm_private?gm_it_private_pc(gm_it_checkpoint):gm_base+it_stock_pc[gm_it_checkpoint];clear.slots[0].address=target;clear.slots[0].control=0x1e5;cio.size=24;nps_debug_dump("tail-debug-arm-request",0,&cio,&clear);rc=pt(0x4205,tid,0x402,(U)&cio);event("tail-debug-arm-set");hex("result",rc);if(rc<0)return 0;
    struct NpsDebugState after={0};struct Iov aio={&after,sizeof(after)};rc=pt(0x4204,tid,0x402,(U)&aio);nps_debug_dump("tail-debug-arm-after",rc,&aio,&after);if(rc<0||aio.size!=sizeof(after)||after.info!=before.info||after.slots[0].address!=target||after.slots[0].control!=0x1e4U)return 0;for(int i=1;i<16;i++)if(after.slots[i].address||after.slots[i].control)return 0;
    event("tail-debug-ready");hex("checkpoint",gm_it_checkpoint);hex("tid",tid);hex("target",target);hex("opcode",(unsigned)peek(tid,target));return 1;
}
static int gm_it_prepare_nonempty(U tid,struct Regs *before_regs) {
    struct NpsDebugState before={0};struct Iov io={&before,sizeof(before)};S rc=pt(0x4204,tid,0x402,(U)&io);nps_debug_dump("tail-debug-prep-before",rc,&io,&before);
    if(rc<0||io.size!=sizeof(before)||before.info!=0x0606||before.slots[0].address||before.slots[0].control!=0x1e5U)return 0;for(int i=1;i<16;i++)if(before.slots[i].address||before.slots[i].control)return 0;
    U target=gm_it_private_pc(0);before.slots[0].address=target;before.slots[0].control=0x1e5;io.size=24;nps_debug_dump("tail-debug-prep-arm-request",0,&io,&before);rc=pt(0x4205,tid,0x402,(U)&io);event("tail-debug-prep-arm-set");hex("result",rc);if(rc<0)return 0;
    struct NpsDebugState after={0};struct Iov aio={&after,sizeof(after)};rc=pt(0x4204,tid,0x402,(U)&aio);nps_debug_dump("tail-debug-prep-arm-after",rc,&aio,&after);if(rc<0||aio.size!=sizeof(after)||after.info!=before.info||after.slots[0].address!=target||after.slots[0].control!=0x1e4U)return 0;for(int i=1;i<16;i++)if(after.slots[i].address||after.slots[i].control)return 0;
    struct Regs after_regs={0};registers(tid,&after_regs,0);gm_registers("tail-debug-prep-registers",tid,&after_regs);if(!gm_regs_same(before_regs,&after_regs))return 0;
    event("tail-debug-prep-ready");hex("checkpoint",0);hex("tid",tid);hex("target",target);hex("opcode",(unsigned)peek(tid,target));return 1;
}
static int gm_ri_binding(void) {
    for(unsigned i=0;i<RI_BINDINGS;i++) { U actual=gm_private?gm->ri_slots[i]:peek(tg_pid,gm_base+ri_binding_slot[i]); U expected=gm_private?gm_ri_private_target(i):gm_base+ri_binding_target[i];
        event("remaining-binding"); hex("index",i); hex("slot",ri_binding_slot[i]); hex("expected_target",expected); hex("actual_target",actual); hex("match",actual==expected); if(actual!=expected)return 0; }
    return 1;
}
static int gm_ri_literals(void) {
    static const U off[3]={0x99814f,0x99364b,0x998f93}; static const char *expect[3]={gm_ri_tty,gm_ri_gpio,gm_ri_command};
    for(unsigned i=0;i<3;i++) { char actual[32]={0}; U address=gm_private?(U)expect[i]:gm_base+off[i]; remote_string(tg_pid,address,actual,sizeof(actual)); int match=equal(actual,expect[i]); U aw0=0,aw1=0,ew0=0,ew1=0,n=0,en=0; while(actual[n]&&n<31)n++; while(expect[i][en])en++; for(unsigned j=0;j<8;j++){aw0|=(U)(unsigned char)actual[j]<<(8*j);if(j<en)ew0|=(U)(unsigned char)expect[i][j]<<(8*j);} for(unsigned j=0;j<8;j++){aw1|=(U)(unsigned char)actual[8+j]<<(8*j);if(8+j<en)ew1|=(U)(unsigned char)expect[i][8+j]<<(8*j);}
        event("remaining-literal"); hex("index",i); hex("address",address); hex("length",n); hex("actual_word0",aw0); hex("actual_word1",aw1); hex("expected_word0",ew0); hex("expected_word1",ew1); hex("match",match); if(!match)return 0; }
    return 1;
}
static int gm_ri_initial(void) {
    if(!gm_ri_binding()||!gm_ri_literals())return 0;
    unsigned scu=gm_private?gm->ri_scu:(unsigned)peek(tg_pid,gm_base+0x3cb4620);
    event("remaining-state"); put("phase = \"initial\"\n"); hex("index",0); hex("object",gm_private?(U)&gm->ri_scu:gm_base+0x3cb4620); hex("width",4); hex("expected",0x80000000); hex("actual",scu); hex("match",scu==0x80000000);
    return scu==0x80000000;
}
static U gm_it_private_target(unsigned i) {
    static const U f[13]={(U)gm_tail_private,(U)gm_tail_private,(U)gm_write,(U)gm_tail_private,(U)gm_tail_private,(U)gm_tail_private,(U)gm_write,(U)gm_tail_private,(U)gm_tail_private,(U)gm_tail_private,(U)gm_tail_private,(U)gm_first,(U)gm_tail_private};
    if(i<13)return f[i];if(i==13)return (U)&gm->it_control;if(i==14)return (U)&gm->it_status;return (U)&gm->it_dac;
}
static int gm_it_live(const char *phase) {
    for(unsigned i=0;i<IT_BINDINGS;i++) { U actual=gm_private?gm->it_slots[i]:peek(tg_pid,gm_base+it_binding_slot[i]);U expected=gm_private?gm_it_private_target(i):gm_base+it_binding_target[i];event("tail-binding");put("phase = \"");put(phase);put("\"\n");hex("index",i);hex("slot",it_binding_slot[i]);hex("expected_target",expected);hex("actual_target",actual);hex("match",actual==expected);if(actual!=expected)return 0; }
    unsigned dac=gm_private?gm->it_dac:(unsigned)peek(tg_pid,gm_base+0x3cb4550),control=gm_private?gm->it_control:(unsigned)peek(tg_pid,gm_base+0x3cb44fc);
    unsigned domain=gm_private?gm->st_globals[0]:(unsigned)peek(tg_pid,gm_base+0xb8f4e4),series=gm_private?gm->st_globals[1]:(unsigned)peek(tg_pid,gm_base+0xb8f4e8);
    U record=gm_private?(U)&gm->st_series[2][0]:gm_base+0xb8f530,config=gm_private?((U)gm->st_series[2][6]|((U)gm->st_series[2][7]<<32)):peek(tg_pid,gm_base+0xb8f548),expected_config=gm_private?(U)&gm->st_configs[1]:gm_base+0xb8f478;
    event("tail-state");put("phase = \"");put(phase);put("\"\n");hex("index",7);hex("object",gm_private?(U)&gm->st_series[2][6]:gm_base+0xb8f548);hex("actual",config);hex("expected",expected_config);hex("match",config==expected_config);if(config!=expected_config)return 0;
    unsigned field=gm_private?gm->st_configs[1]:(unsigned)peek(tg_pid,config+0x68);
    unsigned rec0=gm_private?gm->st_series[2][0]:(unsigned)peek(tg_pid,record),rec1=gm_private?gm->st_series[2][1]:(unsigned)peek(tg_pid,record+4);
    unsigned actual[7]={dac>>16,control,domain,series,rec0,rec1,field};unsigned expected[7]={0,0,8,900,8,900,1};
    U object[7]={gm_private?(U)&gm->it_dac:gm_base+0x3cb4550,gm_private?(U)&gm->it_control:gm_base+0x3cb44fc,gm_private?(U)&gm->st_globals[0]:gm_base+0xb8f4e4,gm_private?(U)&gm->st_globals[1]:gm_base+0xb8f4e8,record,record+4,gm_private?(U)&gm->st_configs[1]:config+0x68};
    for(unsigned i=0;i<7;i++){event("tail-state");put("phase = \"");put(phase);put("\"\n");hex("index",i);hex("object",object[i]);hex("actual",actual[i]);hex("expected",expected[i]);hex("match",actual[i]==expected[i]);if(actual[i]!=expected[i])return 0;}
    return 1;
}
static void gm_it_reject(U tid,const char *reason,const char *stage,U actual,U expected) { event("tail-rejected");put("reason = \"");put(reason);put("\"\nstage = \"");put(stage);put("\"\n");hex("tid",tid);hex("checkpoint",gm_it_checkpoint);hex("reads",gm_it_reads);hex("writes",gm_it_writes);hex("actual",actual);hex("expected",expected);gm_quiesce(tid);quit(78); }
static int gm_it_checkpoint_ok(unsigned i,struct Regs *r) {
    unsigned er=i?10:3,ew=i?2:1;if(gm_it_reads!=er||gm_it_writes!=ew)return 0;
    U packed=gm_private?gm->it_packed:(unsigned)peek(tg_pid,r->x[29]-0x48),hw=gm_private?gm->it_hw:(unsigned)peek(tg_pid,r->x[29]-0x4c);
    event("tail-parent-output");hex("checkpoint",i);hex("index",0);hex("object",gm_private?(U)&gm->it_packed:r->x[29]-0x48);hex("width",4);hex("actual",packed);hex("expected",0x12345678);hex("match",packed==0x12345678);
    event("tail-parent-output");hex("checkpoint",i);hex("index",1);hex("object",gm_private?(U)&gm->it_hw:r->x[29]-0x4c);hex("width",4);hex("actual",hw);hex("expected",0x10203040);hex("match",hw==0x10203040);
    if(packed!=0x12345678||hw!=0x10203040)return 0;
    if(!i){U object=gm_private?(U)&gm->it_dac:gm_base+0x3cb4550;unsigned dac=(unsigned)peek(tg_pid,object);event("tail-parent-output");hex("checkpoint",i);hex("index",11);hex("object",object);hex("width",4);hex("actual",dac);hex("expected",0x646e);hex("match",dac==0x646e);return (gm_private||(unsigned)r->x[10]==1)&&dac==0x646e&&gm_it_live("checkpoint0");}
    static const U expect[6]={0x21,0x345,0x234,0x456,0x167,0};
    for(unsigned j=0;j<6;j++){U object=gm_private?(U)&gm->it_taps[j]:r->x[29]-(j==0?0x50:j==1?0x58:j==2?0x60:j==3?0x68:j==4?0x70:0x74);U actual=gm_private?gm->it_taps[j]:(j==0||j==5?(unsigned)peek(tg_pid,object):peek(tg_pid,object));unsigned width=(j==0||j==5)?4:8;event("tail-parent-output");hex("checkpoint",i);hex("index",j+2);hex("object",object);hex("width",width);hex("actual",actual);hex("expected",expect[j]);hex("match",actual==expect[j]);if(actual!=expect[j])return 0;}
    unsigned ready=gm_private?gm->it_ready:(unsigned)peek(tg_pid,r->x[29]-0x78)&255,status=gm_private?gm->it_status:(unsigned)peek(tg_pid,gm_base+0x3cb4540),control=gm_private?gm->it_control:(unsigned)peek(tg_pid,gm_base+0x3cb44fc),dac=gm_private?gm->it_dac:(unsigned)peek(tg_pid,gm_base+0x3cb4550);
    U actuals[4]={ready,status,control,dac},expects[4]={1,0x20000000,0,0x646e},objects[4]={gm_private?(U)&gm->it_ready:r->x[29]-0x78,gm_private?(U)&gm->it_status:gm_base+0x3cb4540,gm_private?(U)&gm->it_control:gm_base+0x3cb44fc,gm_private?(U)&gm->it_dac:gm_base+0x3cb4550};for(unsigned j=0;j<4;j++){event("tail-parent-output");hex("checkpoint",i);hex("index",j+8);hex("object",objects[j]);hex("width",j?4:1);hex("actual",actuals[j]);hex("expected",expects[j]);hex("match",actuals[j]==expects[j]);if(actuals[j]!=expects[j])return 0;}
    if(i==1&&(unsigned)r->x[0]!=0)return 0;return 1;
}
static int gm_regs_same(struct Regs *a,struct Regs *b) { for(int i=0;i<31;i++)if(a->x[i]!=b->x[i])return 0; return a->pc==b->pc&&a->sp==b->sp&&a->pstate==b->pstate; }
static int gm_ri_checkpoint_ok(unsigned i,struct Regs *r,int cached,unsigned boolean,unsigned la) {
    if(gm_ri_writes!=2)return 0;
    S x0=(S)(int)(unsigned)r->x[0]; if(i==0)return r->x[0]==(gm_private?(U)gm_ri_tty:gm_base+0x99814f)&&r->x[1]==1;
    if(i==1)return x0<0; if(i==2)return x0==-1&&!boolean;
    if(i==3) { return r->x[0]==(gm_private?(U)gm_ri_command:gm_base+0x998f93)&&r->x[1]==5&&cached<0; }
    if(i==4)return r->x[0]==(gm_private?(U)gm_ri_gpio:gm_base+0x99364b)&&r->x[1]==0x802;
    if(i==5)return x0<0; if(i==6)return x0==-3; if(i==7)return x0==-7; if(i==8)return x0==-3;
    return x0==-1&&cached==-7&&la==0;
}
static void gm_ri_reject(U tid,const char *reason,U actual,U expected) { event("remaining-rejected"); put("reason = \""); put(reason); put("\"\n"); hex("tid",tid); hex("checkpoint",gm_ri_checkpoint); hex("actual",actual); hex("expected",expected); gm_quiesce(tid); quit(78); }
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
        if(gm_remaining&&gm_writes>=AT_FULL_WRITES+ST_WRITES&&!quiescing) { gm_region_clone=child; event("remaining-clone"); hex("parent_tid",tid); hex("new_tid",child); return 1; }
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
    if(gm_remaining) tg_deadline=tg_now()+2000;
    event("terminal-quiesce"); hex("stopping_tid",stopping_tid);
    for(U i=0;i<tg_count;i++) if(tg_threads[i].live && !tg_threads[i].stopped) {
        S rc=pt(0x4207,tg_threads[i].tid,0,0); event("terminal-interrupt"); hex("tid",tg_threads[i].tid); hex("result",rc);
        if(rc<0 && rc!=-5) tg_fail("terminal-interrupt",rc);
    }
    for(;;) {
        int pending=0; for(U i=0;i<tg_count;i++) if(tg_threads[i].live && !tg_threads[i].stopped) pending=1;
        if(!pending) break;
        int status=0; U tid=gm_wait(&status); if(!tid) { event("terminal-cleanup-deadline"); hex("stopping_tid",stopping_tid); tg_deadline=tg_now()+2000; tg_cleanup(); quit(84); } if(gm_meta(tid,status,1)) continue;
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
    if(gm_remaining) { event("remaining-summary"); hex("private_metrics",gm_private); hex("scu_object",gm_private?(U)&gm->ri_scu:gm_base+0x3cb4620); hex("scu_value",gm_private?gm->ri_scu:(unsigned)peek(tg_pid,gm_base+0x3cb4620)); hex("la_object",gm_private?(U)&gm->ri_la:gm_base+0x106d4d8); hex("la_value",gm_private?gm->ri_la:(unsigned)peek(tg_pid,gm_base+0x106d4d8)); hex("cached_object",gm_private?(U)&gm->ri_cached:gm_base+0xbb127c); hex("cached_value",(unsigned)(gm_private?gm->ri_cached:(int)peek(tg_pid,gm_base+0xbb127c))); hex("checkpoints",gm_ri_checkpoint); hex("remaining_writes",gm_ri_writes); hex("total_writes",gm_writes); hex("atomic",gm_private?gm->ri_atomic:0); hex("device_io",gm_private?gm->ri_device_io:0); hex("old_executed",gm_private?gm->ri_old_executed:0); hex("clone_tid",gm_region_clone); }
    if(gm_tail) { event("tail-summary");hex("private_metrics",gm_private);hex("reads",gm_it_reads);hex("writes",gm_it_writes);hex("checkpoints",gm_it_checkpoint);hex("total_writes",gm_writes);hex("atomic",gm_private?gm->it_atomic:0);hex("calibration_executed",gm_private?gm->it_calibration:0);hex("old_executed",gm_private?gm->it_old:0);hex("clone_tid",gm_region_clone); }
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
    if(gm_remaining) { event("remaining-mode"); put("debug_profile = \"phase-specific-clear-v1\"\n"); hex("checkpoint_count",RI_CHECKPOINTS); hex("write_count",RI_WRITES); hex("binding_count",RI_BINDINGS); hex("deadline_ms",10000); }
    if(gm_tail) { event("tail-mode");put("debug_profile = \"inherited-direct-arm-v1\"\n");hex("read_count",IT_READS);hex("write_count",IT_WRITES);hex("checkpoint_count",IT_CHECKPOINTS);hex("binding_count",IT_BINDINGS);hex("deadline_ms",10000); }
    if(private) gm_publish(&gm->release);
    for(U i=0;i<tg_count;i++) if(tg_threads[i].live) gm_resume(&tg_threads[i]);
    U fd=(U)-1; int pending_open=0,pending_map=0;
    for(;;) {
        int status=0; U tid=gm_wait(&status);
        if(!tid && gm_remaining) { event(gm_tail?"tail-deadline":"remaining-deadline"); hex("stopping_tid",0); hex("checkpoint",gm_tail?gm_it_checkpoint:gm_ri_checkpoint); hex("reads",gm_it_reads); hex("remaining_writes",gm_ri_writes); hex("tail_writes",gm_it_writes); gm_quiesce(0); quit(78); }
        if(gm_meta(tid,status,0)) { if(gm_region_clone) { if(gm_tail&&gm_ri_checkpoint==RI_CHECKPOINTS)gm_it_reject(tid,"clone","runtime",gm_region_clone,0);gm_ri_reject(tid,"clone",gm_region_clone,0); } continue; }
        U signal=(status>>8)&255; struct TgThread *t=tg_find(tid); struct Regs r={0}; registers(tid,&r,0);
        if(gm_remaining&&signal==5&&gm_writes>=AT_FULL_WRITES+ST_WRITES&&gm_ri_checkpoint<RI_CHECKPOINTS) {
            U info[16]={0}; check(pt(0x4202,tid,0,(U)info),"remaining-siginfo"); unsigned i=gm_ri_checkpoint;
            U target=private?gm_ri_private_pc(i):base+ri_stock_pc[i],opcode=(unsigned)peek(tid,r.pc);
            unsigned expected_opcode=private?0xd503201f:ri_stock_opcode[i]; event("remaining-checkpoint"); hex("index",i); hex("tid",tid); hex("signal",signal); hex("si_code",(unsigned)info[1]); hex("address",info[2]); hex("pc",r.pc); hex("relative_pc",private?0:r.pc-base); hex("opcode",opcode); hex("expected_pc",target); hex("expected_opcode",expected_opcode);
            gm_registers("remaining-checkpoint-registers",tid,&r);
            if(tid!=pid||(unsigned)info[1]!=4||info[2]!=target||r.pc!=target||opcode!=expected_opcode)gm_ri_reject(tid,"checkpoint",r.pc,target);
            int cached=private?gm->ri_cached:(int)(unsigned)peek(tg_pid,base+0xbb127c); unsigned boolean=private?gm->ri_bool:(i==2?(unsigned)peek(tg_pid,r.x[29]-1)&255:0); unsigned la=private?gm->ri_la:(unsigned)peek(tg_pid,base+0x106d4d8);
            int guard=gm_ri_checkpoint_ok(i,&r,cached,boolean,la); event("remaining-checkpoint-guard"); hex("index",i); hex("match",guard); hex("atomic",private?gm->ri_atomic:0); hex("x0",r.x[0]); hex("x1",r.x[1]); hex("cached_object",private?(U)&gm->ri_cached:base+0xbb127c); hex("cached_value",(unsigned)cached); hex("bool_object",private?(U)&gm->ri_bool:(i==2?r.x[29]-1:0)); hex("bool_value",boolean); hex("la_object",private?(U)&gm->ri_la:base+0x106d4d8); hex("la_value",la); if(!guard)gm_ri_reject(tid,"checkpoint-state",r.x[0],0);
            struct Regs before=r; gm_ri_checkpoint++; if(!gm_ri_debug(tid,gm_ri_checkpoint<RI_CHECKPOINTS))gm_ri_reject(tid,"debug-rotation",gm_ri_checkpoint,RI_CHECKPOINTS);
            struct Regs after={0}; registers(tid,&after,0); gm_registers("remaining-debug-registers",tid,&after); if(!gm_regs_same(&before,&after))gm_ri_reject(tid,"debug-registers",after.pc,before.pc);
            gm_resume(t); continue;
        }
        if(gm_tail&&signal==5&&gm_ri_checkpoint==RI_CHECKPOINTS&&gm_it_checkpoint<IT_CHECKPOINTS) {
            U info[16]={0};check(pt(0x4202,tid,0,(U)info),"tail-siginfo");unsigned i=gm_it_checkpoint;U target=private?gm_it_private_pc(i):base+it_stock_pc[i],opcode=(unsigned)peek(tid,r.pc),expected_opcode=private?0xd503201f:it_stock_opcode[i];
            event("tail-checkpoint");hex("index",i);hex("tid",tid);hex("signal",signal);hex("si_code",(unsigned)info[1]);hex("address",info[2]);hex("pc",r.pc);hex("relative_pc",private?0:r.pc-base);hex("opcode",opcode);hex("expected_pc",target);hex("expected_opcode",expected_opcode);hex("reads",gm_it_reads);hex("writes",gm_it_writes);gm_registers("tail-checkpoint-registers",tid,&r);
            if(tid!=pid||(unsigned)info[1]!=4||info[2]!=target||r.pc!=target||opcode!=expected_opcode)gm_it_reject(tid,"checkpoint","trap",r.pc,target);
            int guard=gm_it_checkpoint_ok(i,&r);event("tail-checkpoint-guard");hex("index",i);hex("match",guard);hex("reads",gm_it_reads);hex("writes",gm_it_writes);hex("atomic",private?gm->it_atomic:0);if(!guard)gm_it_reject(tid,"checkpoint-state","guard",i,1);
            struct Regs before=r;gm_it_checkpoint++;if(!gm_it_debug(tid,gm_it_checkpoint<IT_CHECKPOINTS))gm_it_reject(tid,"debug-rotation","checkpoint",gm_it_checkpoint,IT_CHECKPOINTS);struct Regs after={0};registers(tid,&after,0);gm_registers("tail-debug-registers",tid,&after);if(!gm_regs_same(&before,&after))gm_it_reject(tid,"debug-registers","checkpoint",after.pc,before.pc);
            if(gm_it_checkpoint==IT_CHECKPOINTS){gm_quiesce(tid);quit(78);}gm_resume(t);continue;
        }
        if(signal==11 || (gm_next && signal==7)) {
            gm_fault(tid,"mapped-fault",signal); U info[16]={0}; check(pt(0x4202,tid,0,(U)info),"response-siginfo");
            if(gm_next && gm_responses==2) {
                U offset=info[2]-gm_mapping,write_pc=private?(U)gm_write_pc:base+0x27043c;
                if(gm_tail&&gm_ri_checkpoint==RI_CHECKPOINTS&&gm_writes>=AT_FULL_WRITES+ST_WRITES+RI_WRITES) {
                    unsigned step=gm_it_reads+gm_it_writes,read_index=99,write_index=99;int expect_read=0,expect_write=0;
                    if(step<3){expect_read=1;read_index=step;}else if(step==3){expect_write=1;write_index=0;}else if(step>=4&&step<=8){expect_read=1;read_index=step-1;}else if(step==9){expect_write=1;write_index=1;}else if(step>=10&&step<=11){expect_read=1;read_index=step-2;}
                    int phase=(step<4?gm_it_checkpoint==0:step<12?gm_it_checkpoint==1:gm_it_checkpoint==2);
                    if(!gm_it_reads&&!gm_it_writes&&tid==pid&&signal==11&&(unsigned)info[1]==2&&offset==it_read_offset[0]&&r.x[8]==info[2]&&r.pc==(private?(U)gm_first_pc:base+0x270604)&&(unsigned)peek(tid,r.pc)==0xb9400109) { if(private&&gm->arm==75&&!gm_it_prepare_nonempty(tid,&r))gm_it_reject(tid,"debug-preparation","initial",0,1);if(!gm_it_live("initial"))gm_it_reject(tid,"live-state","initial",0,1);if(!gm_it_debug(tid,1))gm_it_reject(tid,"debug-initial","initial",0,1);struct Regs da={0};registers(tid,&da,0);gm_registers("tail-initial-debug-registers",tid,&da);if(!gm_regs_same(&r,&da))gm_it_reject(tid,"debug-registers","initial",da.pc,r.pc); }
                    U read_pc=private?(U)gm_first_pc:base+0x270604,actual_opcode=(unsigned)peek(tid,r.pc);int mapped=gm_mapping&&info[2]>=gm_mapping&&info[2]<gm_mapping+0x1000000;
                    if(expect_read&&phase&&tid==pid&&signal==11&&(unsigned)info[1]==2&&offset==it_read_offset[read_index]&&r.x[8]==info[2]&&r.pc==read_pc&&actual_opcode==0xb9400109) {
                        struct Regs before=r;r.x[9]=it_read_value[read_index];r.pc+=4;registers(tid,&r,1);struct Regs after={0};registers(tid,&after,0);if(!gm_regs_same(&r,&after))gm_it_reject(tid,"read-registers","read",after.pc,r.pc);gm_it_reads++;
                        event("tail-read");hex("tid",tid);hex("index",read_index);hex("offset",offset);hex("value",it_read_value[read_index]);hex("width",4);hex("pc",before.pc);hex("opcode",0xb9400109);gm_registers("tail-read-registers",tid,&after);gm_resume(t);continue;
                    }
                    if(expect_write&&phase&&tid==pid&&signal==11&&(unsigned)info[1]==2&&offset==it_write_offset[write_index]&&r.x[8]==info[2]&&r.pc==write_pc&&actual_opcode==0xb9000109&&(unsigned)r.x[9]==it_write_value[write_index]) {
                        U state_object=write_index?(private?(U)&gm->it_control:base+0x3cb44fc):(private?(U)&gm->it_dac:base+0x3cb4550);unsigned state=(unsigned)peek(tg_pid,state_object),state_expected=it_write_value[write_index];event("tail-state");put("phase = \"");put(write_index?"write1":"write0");put("\"\n");hex("index",8+write_index);hex("object",state_object);hex("actual",state);hex("expected",state_expected);hex("match",state==state_expected);if(state!=state_expected)gm_it_reject(tid,"live-state",write_index?"write1":"write0",state,state_expected);
                        struct Regs before=r;r.pc+=4;registers(tid,&r,1);struct Regs after={0};registers(tid,&after,0);if(!gm_regs_same(&r,&after))gm_it_reject(tid,"write-registers","write",after.pc,r.pc);gm_it_writes++;gm_writes++;gm_write_offset=offset;gm_write_value=(unsigned)before.x[9];event("modeled-write");hex("tid",tid);hex("index",gm_writes-1);hex("offset",offset);hex("value",gm_write_value);hex("width",4);event("tail-write");hex("tid",tid);hex("index",write_index);hex("global_index",gm_writes-1);hex("offset",offset);hex("value",gm_write_value);hex("width",4);hex("pc",before.pc);hex("opcode",0xb9000109);gm_registers("write-registers",tid,&after);gm_resume(t);continue;
                    }
                    const char *reason=!phase?"phase":tid!=pid?"thread":signal!=11?"signal":(unsigned)info[1]!=2?"si-code":expect_read&&actual_opcode==0xf9400109?"width":expect_read&&offset!=it_read_offset[read_index]?"order":expect_write&&offset!=it_write_offset[write_index]?"offset":r.x[8]!=info[2]?"address-register":expect_read&&r.pc!=read_pc?"pc":expect_write&&r.pc!=write_pc?"pc":expect_write&&(unsigned)r.x[9]!=it_write_value[write_index]?"value":"extra-access";
                    event("tail-access-rejected");put("reason = \"");put(reason);put("\"\n");hex("tid",tid);hex("step",step);hex("reads",gm_it_reads);hex("writes",gm_it_writes);hex("offset",offset);hex("pc",r.pc);hex("opcode",actual_opcode);hex("actual_value",(unsigned)r.x[9]);hex("expected_offset",expect_read?it_read_offset[read_index]:expect_write?it_write_offset[write_index]:0);hex("expected_value",expect_read?it_read_value[read_index]:expect_write?it_write_value[write_index]:0);gm_it_reject(tid,reason,"access",offset,expect_read?it_read_offset[read_index]:expect_write?it_write_offset[write_index]:0);event("unsupported-access");hex("tid",tid);put("classification = \"");put(mapped?"mapped":"nonmapped");put("\"\n");quit(78);
                }
                if(gm_remaining&&gm_writes>=AT_FULL_WRITES+ST_WRITES) {
                    unsigned index=gm_ri_writes; int has=index<RI_WRITES,mapped=gm_mapping&&info[2]>=gm_mapping&&info[2]<gm_mapping+0x1000000;
                    U eo=has?ri_offset[index]:4,ev=has?ri_value[index]:0; int phase=(index<2?gm_ri_checkpoint==0:gm_ri_checkpoint==RI_CHECKPOINTS);
                    int candidate=has&&phase&&tid==pid&&signal==11&&(unsigned)info[1]==2&&offset==eo&&r.x[8]==info[2]&&r.pc==write_pc&&(unsigned)peek(tid,r.pc)==0xb9000109&&(unsigned)r.x[9]==ev,live=1;
                    if(candidate&&index==0&&!gm_ri_initial()){live=0;candidate=0;}
                    if(candidate&&index==2) { unsigned la=private?gm->ri_la:(unsigned)peek(tg_pid,base+0x106d4d8); event("remaining-state"); put("phase = \"la\"\n"); hex("index",1); hex("object",private?(U)&gm->ri_la:base+0x106d4d8); hex("width",4); hex("expected",1); hex("actual",la); hex("match",la==1); if(la!=1){live=0;candidate=0;} }
                    if(candidate) { struct Regs before=r; r.pc+=4; registers(tid,&r,1); struct Regs after={0}; registers(tid,&after,0); if(!gm_regs_same(&r,&after))gm_ri_reject(tid,"write-registers",after.pc,r.pc);
                        gm_write_offset=offset; gm_write_value=(unsigned)before.x[9]; gm_writes++; gm_ri_writes++;
                        event("modeled-write"); hex("tid",tid); hex("index",gm_writes-1); hex("offset",offset); hex("value",gm_write_value); hex("width",4);
                        event("remaining-write"); hex("tid",tid); hex("index",index); hex("global_index",gm_writes-1); hex("pc",before.pc); hex("opcode",0xb9000109); hex("offset",offset); hex("value",gm_write_value); hex("width",4); gm_registers("write-registers",tid,&after);
                        if(gm_ri_writes==2) { gm_ri_checkpoint=0; if(!gm_ri_debug(tid,1))gm_ri_reject(tid,"debug-initial",0,1); struct Regs debug_after={0}; registers(tid,&debug_after,0); gm_registers("remaining-initial-debug-registers",tid,&debug_after); if(!gm_regs_same(&after,&debug_after))gm_ri_reject(tid,"debug-initial-registers",debug_after.pc,after.pc); }
                        gm_resume(t); continue;
                    }
                    event(has?"remaining-write-rejected":"remaining-boundary"); if(has){const char *reason=!phase?"phase":tid!=pid?"thread":signal!=11?"signal":(unsigned)info[1]!=2?"si-code":offset!=eo?"offset":r.x[8]!=info[2]?"address-register":r.pc!=write_pc?"pc":(unsigned)peek(tid,r.pc)!=0xb9000109?"opcode":!live?"live-state":"value"; put("reason = \"");put(reason);put("\"\n");} hex("tid",tid); hex("index",index); hex("global_index",gm_writes); hex("signal",signal); hex("si_code",(unsigned)info[1]); hex("address",info[2]); hex("offset",offset); hex("pc",r.pc); hex("opcode",(unsigned)peek(tid,r.pc)); hex("actual_value",(unsigned)r.x[9]); hex("expected_offset",eo); hex("expected_value",ev); hex("remaining_writes",gm_ri_writes);
                    if(!has&&gm_ri_checkpoint==RI_CHECKPOINTS&&tid==pid&&signal==11&&(unsigned)info[1]==2&&offset==4&&r.x[8]==info[2]&&r.pc==(private?(U)gm_second_pc:base+0x270604)&&(unsigned)peek(tid,r.pc)==0xb9400109) { gm_quiesce(tid); quit(78); }
                    event("unsupported-access"); hex("tid",tid); hex("responses",gm_responses); hex("writes",gm_writes); put("classification = \""); put(mapped?"mapped":"nonmapped"); put("\"\n"); gm_quiesce(tid); quit(mapped?78:83);
                }
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
    int tail_control=argc==5&&equal(argv[1],"control-tail"),tail_stock=argc==6&&equal(argv[1],"stock-tail");
    if(tail_control||tail_stock) {
        U arm=tail_control?parse(argv[2],10):0;if(tail_control&&(arm<59||arm>75))quit(2);unsigned profile=tail_stock?1:2;
        if(!gm_at_load(argv[tail_stock?4:3],profile,AT_FULL_WRITES))quit(2);if(!gm_st_load(argv[tail_stock?5:4],profile))quit(2);
        gm_transcript=1;gm_spu=1;gm_remaining=1;gm_tail=1;gm_next=1;tg_deadline=tg_now()+10000;
        if(tail_stock){U pid=parse(argv[2],10),base=parse(argv[3],16);event("model-mode");put("scope = \"stock\"\n");hex("pid",pid);hex("continuation",1);hex("one_write",0);hex("pair_write",0);hex("transcript",1);hex("spu",1);hex("remaining",1);hex("tail",1);hex("profile",1);hex("write_count",AT_FULL_WRITES);hex("spu_write_count",ST_WRITES);hex("remaining_write_count",RI_WRITES);hex("tail_read_count",IT_READS);hex("tail_write_count",IT_WRITES);hex("tail_checkpoint_count",IT_CHECKPOINTS);gm_observe(pid,base,0);quit(2);}
        S memory=sys(222,0,32768,3,0x21,(U)-1,0);check(memory,"model-shared-mmap");gm=(struct GmShared *)memory;gm->arm=arm;gm->output=(U)-1;U observer=sys(172,0,0,0,0,0,0);S pid=sys(220,17,0,0,0,0,0);check(pid,"model-private-clone");if(!pid)gm_private_leader(observer);while(!gm_load(&gm->ready))tg_tick();
        event("model-mode");put("scope = \"private\"\n");hex("arm",arm);hex("pid",pid);hex("fixture_worker",gm->worker);hex("continuation",1);hex("one_write",0);hex("pair_write",0);hex("transcript",1);hex("spu",1);hex("remaining",1);hex("tail",1);hex("profile",2);hex("write_count",AT_FULL_WRITES);hex("spu_write_count",ST_WRITES);hex("remaining_write_count",RI_WRITES);hex("tail_read_count",IT_READS);hex("tail_write_count",IT_WRITES);hex("tail_checkpoint_count",IT_CHECKPOINTS);gm_observe(pid,0,1);quit(2);
    }
    int remaining_control=argc==5&&equal(argv[1],"control-remaining"),remaining_stock=argc==6&&equal(argv[1],"stock-remaining");
    if(remaining_control||remaining_stock) {
        U arm=remaining_control?parse(argv[2],10):0; if(remaining_control&&(arm<40||arm>58))quit(2); unsigned profile=remaining_stock?1:2;
        if(!gm_at_load(argv[remaining_stock?4:3],profile,AT_FULL_WRITES))quit(2); if(!gm_st_load(argv[remaining_stock?5:4],profile))quit(2);
        gm_transcript=1; gm_spu=1; gm_remaining=1; gm_next=1; tg_deadline=tg_now()+10000;
        if(remaining_stock) { U pid=parse(argv[2],10),base=parse(argv[3],16); event("model-mode"); put("scope = \"stock\"\n"); hex("pid",pid); hex("continuation",1); hex("one_write",0); hex("pair_write",0); hex("transcript",1); hex("spu",1); hex("remaining",1); hex("profile",1); hex("write_count",AT_FULL_WRITES); hex("spu_write_count",ST_WRITES); hex("remaining_write_count",RI_WRITES); gm_observe(pid,base,0); quit(2); }
        S memory=sys(222,0,32768,3,0x21,(U)-1,0); check(memory,"model-shared-mmap"); gm=(struct GmShared *)memory; gm->arm=arm; gm->output=(U)-1; U observer=sys(172,0,0,0,0,0,0);
        S pid=sys(220,17,0,0,0,0,0); check(pid,"model-private-clone"); if(!pid)gm_private_leader(observer); while(!gm_load(&gm->ready))tg_tick();
        event("model-mode"); put("scope = \"private\"\n"); hex("arm",arm); hex("pid",pid); hex("fixture_worker",gm->worker); hex("continuation",1); hex("one_write",0); hex("pair_write",0); hex("transcript",1); hex("spu",1); hex("remaining",1); hex("profile",2); hex("write_count",AT_FULL_WRITES); hex("spu_write_count",ST_WRITES); hex("remaining_write_count",RI_WRITES); gm_observe(pid,0,1); quit(2);
    }
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
