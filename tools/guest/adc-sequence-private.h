#ifndef MHO_ADC_SEQUENCE_PRIVATE_H
#define MHO_ADC_SEQUENCE_PRIVATE_H
/* Private observer controls. These are not a substitute implementation of stock ADC helpers. */
extern char gm_ap_cp[],gm_ap_wrong_cp[];
__attribute__((naked)) static void gm_ap_site(void) {
    __asm__ volatile("mov w0, #0\n.global gm_ap_wrong_cp\ngm_ap_wrong_cp:\nnop\n.global gm_ap_cp\ngm_ap_cp:\nnop\nret");
}
static U gm_ap_private_source(unsigned source) {
    switch(source) {
        case AP_SOURCE_ADC_RECORD:return gm->cl_adc;
        case AP_SOURCE_SETTING:return gm->adci_setting;
        case AP_SOURCE_DRV:return gm->adci_drvparam;
        case AP_SOURCE_CONFIG:return gm->adci_config;
        case AP_SOURCE_SAMPLE:return gm->adci_table;
        case AP_SOURCE_LOW:return gm->adci_shadow_low;
        case AP_SOURCE_HIGH:return gm->adci_shadow_high;
        case AP_SOURCE_GLOBAL:return gm->adci_global;
        case AP_SOURCE_SERIES:return gm->adci_series;
        case AP_SOURCE_MASK:return gm->adci_arena+0xc000;
        default:quit(70);
    }
    return 0;
}
static void gm_ap_private_value(const struct ApGuard *g,U value) {
    unsigned char *p=(unsigned char *)(gm_ap_private_source(g->source)+g->offset);
    for(unsigned i=0;i<g->width;i++)p[i]=(unsigned char)(value>>(8*i));
}
static void gm_ap_prepare_fixture(void) {
    gm_cl_fill((unsigned char *)gm->cl_adc,CL_ADC_BYTES,0,0);
    for(unsigned i=0;i<AP_GUARDS;i++)gm_ap_private_value(&ap_guards[i],ap_guards[i].expected);
    gm_adci_u64(gm->adci_global,gm->mapping);
    if(gm->arm==107)gm_adci_u32(gm->adci_config+0x38,250001);
}
static void gm_ap_worker(void) {
    gm_wait_flag(&gm->ap_worker_go);gm_publish(&gm->ap_worker_ack);
    if(gm->arm==108)gm_worker_read(gm->mapping+0x3004);
    gm_wait_flag(&gm->hold);
}
static void gm_ap_fixture(U mapping) {
    gm_publish(&gm->ap_worker_go);gm_wait_flag(&gm->ap_worker_ack);
    if(gm->arm==108||gm->arm==110){gm_wait_flag(&gm->hold);quit(88);}
    if(gm->arm==109){S child=gm_clone(0x10f00,(U)(gm_stack3+sizeof(gm_stack3)),gm_worker2);check(child,"adc-sequence-clone");gm_wait_flag(&gm->hold);quit(88);}
    for(unsigned i=0;i<AP_OPERATIONS;i++) {
        if(gm->arm==104&&i==0)continue;
        unsigned index=gm->arm==103&&i<2?1-i:i;
        const struct ApOperation *op=&ap_operations[index];
        if(gm->arm==105&&i==0)gm_first(mapping+0x3010);
        if(op->read){U value=gm_first(mapping+op->offset);unsigned decoded=(value&0x10000)?(unsigned)value&0xffffU:0;
            if(!gm->ap_reads){gm->ap_raw0=value;gm->ap_protocol0=decoded;}else{gm->ap_raw1=value;gm->ap_protocol1=decoded;}gm->ap_reads++;
        } else gm_write(mapping+op->offset,op->value+(gm->arm==102&&i==0?1U:0U));
    }
    for(unsigned i=0;i<AP_FINAL_SHADOWS;i++)gm_ap_private_value(&ap_final_shadows[i],ap_final_shadows[i].expected);
    if(gm->arm==112)gm_ap_private_value(&ap_final_shadows[0],ap_final_shadows[0].expected+1);
    if(gm->arm!=111)__atomic_add_fetch(&gm->ap_atomic,1,__ATOMIC_SEQ_CST);
    gm_ap_site();gm->ap_old++;quit(88);
}
#endif
