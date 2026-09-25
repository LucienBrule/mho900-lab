#ifndef MHO_ADC_SEQUENCE_OBSERVER_H
#define MHO_ADC_SEQUENCE_OBSERVER_H
static unsigned gm_ap_active,gm_ap_index,gm_ap_reads,gm_ap_writes;
static U gm_ap_source(unsigned source) {
    if(gm_private)return gm_ap_private_source(source);
    static const U offset[AP_SOURCES]={cl_adc_record,cl_scope+0x18,cl_scope+0x5a00,0xb8f478,0xb8f808,0x3cb44fc,0x3cb457c,0xbe1128,0xb8f4e4,0x9948bc};
    return source<AP_SOURCES?gm_base+offset[source]:0;
}
static int gm_ap_read_value(U address,unsigned width,U *value) {
    if(width!=2)return gm_adci_read(address,width,value);
    if(!gm_adci_contains(address,2))return 0;
    unsigned char bytes[2]={0};struct Iov local={bytes,2},remote={(void *)address,2};
    S n=sys(270,tg_pid,(U)&local,1,(U)&remote,1,0);if(n!=2)return 0;*value=(U)bytes[0]|((U)bytes[1]<<8);return 1;
}
static void gm_ap_summary(void) {
    event("adc-sequence-summary");hex("operations",gm_ap_index);hex("writes",gm_ap_writes);hex("reads",gm_ap_reads);
    hex("private_metrics",gm_private);hex("worker_ack",gm_private?gm->ap_worker_ack:0);hex("atomic",gm_private?gm->ap_atomic:0);
    hex("raw0",gm_private?gm->ap_raw0:0);hex("raw1",gm_private?gm->ap_raw1:0);hex("protocol0",gm_private?gm->ap_protocol0:0);
    hex("protocol1",gm_private?gm->ap_protocol1:0);hex("private_reads",gm_private?gm->ap_reads:0);hex("old_executed",gm_private?gm->ap_old:0);
}
static void gm_ap_reject(U tid,const char *reason,const char *stage,U actual,U expected) {
    event("adc-sequence-rejected");put("reason = \"");put(reason);put("\"\nstage = \"");put(stage);put("\"\n");
    hex("tid",tid);hex("index",gm_ap_index);hex("actual",actual);hex("expected",expected);gm_ap_summary();gm_quiesce(tid);quit(78);
}
static U gm_ap_return_pc(void){return gm_private?(U)gm_ap_cp:gm_base+AP_RETURN_PC;}
static int gm_ap_debug(U tid,int arm) {
    struct NpsDebugState before={0};struct Iov io={&before,sizeof(before)};S rc=pt(0x4204,tid,0x402,(U)&io);
    nps_debug_dump("adc-sequence-debug-before",rc,&io,&before);
    U previous=arm?0:gm_ap_return_pc();
    if(rc<0||io.size!=sizeof(before)||before.info!=0x0606||before.slots[0].address!=previous||before.slots[0].control!=(arm?0x1e5U:0x1e4U))return 0;
    for(unsigned i=1;i<16;i++)if(before.slots[i].address||before.slots[i].control)return 0;
    U target=arm?(gm_private&&gm->arm==106?(U)gm_ap_wrong_cp:gm_ap_return_pc()):0;
    before.slots[0].address=target;before.slots[0].control=arm?0x1e5U:0;io.size=24;
    nps_debug_dump("adc-sequence-debug-request",0,&io,&before);rc=pt(0x4205,tid,0x402,(U)&io);event("adc-sequence-debug-set");hex("result",rc);if(rc<0)return 0;
    struct NpsDebugState after={0};struct Iov aio={&after,sizeof(after)};rc=pt(0x4204,tid,0x402,(U)&aio);
    nps_debug_dump("adc-sequence-debug-after",rc,&aio,&after);
    if(rc<0||aio.size!=sizeof(after)||after.info!=0x0606||after.slots[0].address!=target||after.slots[0].control!=(arm?0x1e4U:0x1e5U))return 0;
    for(unsigned i=1;i<16;i++)if(after.slots[i].address||after.slots[i].control)return 0;
    return 1;
}
static void gm_ap_guard_values(U tid,const struct ApGuard *guards,unsigned count,int final) {
    for(unsigned i=0;i<count;i++) {
        const struct ApGuard *g=&guards[i];U address=gm_ap_source(g->source)+g->offset,value=0;
        int read=gm_ap_read_value(address,g->width,&value),match=read&&value==g->expected;
        event(final?"adc-sequence-final-shadow":"adc-sequence-entry-guard");hex("index",i);hex("source",g->source);
        hex("offset",g->offset);hex("address",address);hex("width",g->width);hex("actual",value);hex("expected",g->expected);hex("read_ok",read);hex("match",match);
        if(!match)gm_ap_reject(tid,read?"value":"read",final?"final-shadow":"entry",value,g->expected);
    }
}
static void gm_ap_begin(U tid,struct Regs *before) {
    event("adc-sequence-mode");put("scope = \"");put(gm_private?"private":"stock");put("\"\n");hex("arm",gm_private?gm->arm:0);
    hex("operations",AP_OPERATIONS);hex("guards",AP_GUARDS);hex("final_shadows",AP_FINAL_SHADOWS);hex("synthetic0",0x11234);hex("synthetic1",0);
    hex("return_pc",gm_ap_return_pc());hex("stock_return_relative",AP_RETURN_PC);hex("sleep_observation",0);
    if(tid!=tg_pid)gm_ap_reject(tid,"thread","entry",tid,tg_pid);
    gm_ap_guard_values(tid,ap_guards,AP_GUARDS,0);
    unsigned selected=9;U series=gm_ap_source(AP_SOURCE_SERIES),a=0,b=0;
    for(unsigned i=0;i<9;i++){if(!gm_adci_read(series+12+32*i,4,&a)||!gm_adci_read(series+16+32*i,4,&b))gm_ap_reject(tid,"read","series",i,9);if(a==8&&b==900){selected=i;break;}}
    U mapped=0;if(!gm_adci_read(gm_ap_source(AP_SOURCE_GLOBAL),8,&mapped))gm_ap_reject(tid,"read","mapped-base",0,gm_mapping);
    event("adc-sequence-entry-binding");hex("selected_row",selected);hex("expected_row",2);hex("mapped_base",mapped);hex("expected_mapping",gm_mapping);
    if(selected!=2||mapped!=gm_mapping||!mapped)gm_ap_reject(tid,"binding","entry",selected,2);
    U target=gm_ap_return_pc();unsigned opcode=(unsigned)peek(tid,target),expected=gm_private?0xd503201fU:AP_RETURN_OPCODE;
    if(opcode!=expected)gm_ap_reject(tid,"opcode","return-binding",opcode,expected);
    if(!gm_ap_debug(tid,1))gm_ap_reject(tid,"debug","entry",0,1);
    struct Regs after={0};registers(tid,&after,0);gm_registers("adc-sequence-entry-registers",tid,&after);
    if(!gm_regs_same(before,&after))gm_ap_reject(tid,"registers","entry",after.pc,before->pc);
    gm_ap_active=1;event("adc-sequence-resume-group");hex("threads",tg_count);hex("leader",tg_pid);
    for(U i=0;i<tg_count;i++)if(tg_threads[i].live&&tg_threads[i].stopped)gm_resume(&tg_threads[i]);
}
static void gm_ap_access(U tid,U signal,const U *info,struct Regs *r,struct TgThread *thread) {
    U offset=info[2]-gm_mapping;unsigned opcode=(unsigned)peek(tid,r->pc);
    const struct ApOperation *op=gm_ap_index<AP_OPERATIONS?&ap_operations[gm_ap_index]:0;
    U expected_pc=op&&op->read?(gm_private?(U)gm_first_pc:gm_base+0x270604):(gm_private?(U)gm_write_pc:gm_base+0x27043c);
    unsigned expected_opcode=op&&op->read?0xb9400109U:0xb9000109U;
    event("adc-sequence-access");hex("index",gm_ap_index);hex("tid",tid);hex("signal",signal);hex("si_code",(unsigned)info[1]);
    hex("address",info[2]);hex("offset",offset);hex("pc",r->pc);hex("opcode",opcode);hex("operand",(unsigned)r->x[9]);
    if(tid!=tg_pid)gm_ap_reject(tid,"thread","access",tid,tg_pid);
    if(!op)gm_ap_reject(tid,"extra-access","access",offset,0);
    if(signal!=11||(unsigned)info[1]!=2)gm_ap_reject(tid,"signal","access",signal,11);
    if(!gm_mapping||info[2]<gm_mapping||info[2]>=gm_mapping+0x1000000||r->x[8]!=info[2])gm_ap_reject(tid,"address","access",info[2],r->x[8]);
    if(offset!=op->offset)gm_ap_reject(tid,"offset","access",offset,op->offset);
    if(r->pc!=expected_pc||opcode!=expected_opcode)gm_ap_reject(tid,"instruction","access",r->pc,expected_pc);
    if(!op->read&&(unsigned)r->x[9]!=op->value)gm_ap_reject(tid,"value","access",(unsigned)r->x[9],op->value);
    gm_registers("adc-sequence-before-registers",tid,r);struct Regs expected={0};
    expected.sp=r->sp;expected.pc=r->pc+4;expected.pstate=r->pstate;for(unsigned i=0;i<31;i++)expected.x[i]=r->x[i];
    if(op->read)expected.x[9]=op->value;
    registers(tid,&expected,1);struct Regs after={0};registers(tid,&after,0);
    if(!gm_regs_same(&expected,&after))gm_ap_reject(tid,"registers","access",after.pc,expected.pc);
    event(op->read?"adc-sequence-read":"adc-sequence-write");hex("index",gm_ap_index);hex("sequence_index",op->sequence_index);hex("tid",tid);
    hex("offset",op->offset);hex("value",op->value);hex("width",4);hex("synthetic_response",op->read);
    if(op->read)gm_ap_reads++;else{gm_ap_writes++;gm_writes++;gm_write_offset=op->offset;gm_write_value=op->value;}
    gm_registers("adc-sequence-after-registers",tid,&after);gm_ap_index++;gm_resume(thread);
}
static void gm_ap_finish(U tid,struct Regs *r) {
    U info[16]={0};check(pt(0x4202,tid,0,(U)info),"adc-sequence-return-siginfo");
    U expected=gm_ap_return_pc();unsigned opcode=(unsigned)peek(tid,r->pc);
    event("adc-sequence-return");hex("tid",tid);hex("pc",r->pc);hex("expected_pc",expected);hex("si_code",(unsigned)info[1]);hex("address",info[2]);hex("opcode",opcode);hex("status",(unsigned)r->x[0]);hex("operations",gm_ap_index);gm_registers("adc-sequence-return-registers",tid,r);
    if(tid!=tg_pid||r->pc!=expected||info[2]!=expected||(unsigned)info[1]!=4||opcode!=(gm_private?0xd503201fU:AP_RETURN_OPCODE))gm_ap_reject(tid,"pc","return",r->pc,expected);
    if(gm_ap_index!=AP_OPERATIONS||gm_ap_writes!=97||gm_ap_reads!=2||(unsigned)r->x[0]!=0)gm_ap_reject(tid,"completion","return",gm_ap_index,AP_OPERATIONS);
    gm_cl_converge(tid);gm_ap_guard_values(tid,ap_final_shadows,AP_FINAL_SHADOWS,1);
    if(gm_private&&(gm->ap_atomic!=1||gm->ap_worker_ack!=1||gm->ap_reads!=2||gm->ap_raw0!=0x11234||gm->ap_raw1||gm->ap_protocol0!=0x1234||gm->ap_protocol1||gm->ap_old))gm_ap_reject(tid,"private-state","return",gm->ap_atomic,1);
    if(!gm_ap_debug(tid,0))gm_ap_reject(tid,"debug","return",0,1);
    struct Regs after={0};registers(tid,&after,0);gm_registers("adc-sequence-final-registers",tid,&after);
    if(!gm_regs_same(r,&after))gm_ap_reject(tid,"registers","return",after.pc,r->pc);
    event("adc-sequence-complete");hex("return_instruction_executed",0);gm_ap_summary();gm_quiesce(tid);quit(78);
}
#endif
