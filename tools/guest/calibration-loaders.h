#ifndef MHO_CALIBRATION_LOADERS_H
#define MHO_CALIBRATION_LOADERS_H
#define CL_CHECKPOINTS 4
#define CL_BINDINGS 6
#define CL_CAPTURE_COUNT 5
#define CL_LSB_BYTES 192U
#define CL_ADC_BYTES 1936U
#define CL_VERTICAL_BYTES 0x1b60c0U
#define CL_CHUNK 0x10000U
#define CL_CAPTURE_LIMIT 0x200000U
static const U cl_stock_pc[CL_CHECKPOINTS]={0x333b78,0x333b84,0x333b9c,0x333ba8};
static const unsigned cl_stock_opcode[CL_CHECKPOINTS]={0xb90077e0,0xb90077e0,0xb90077e0,0x97fb9b9e};
static const U cl_binding_slot[CL_BINDINGS]={0xb7c000,0xb79558,0xb7d7a8,0xb7f4d8,0xb77ba8,0xb808c0};
static const U cl_binding_target[CL_BINDINGS]={0x2e5a40,0x2e5a4c,0x333afc,0x366e4c,0x366c20,0x33eac8};
static const U cl_scope=0x10bee40,cl_calibration=0x10c4f18,cl_adc=0x10c4f30,cl_vertical=0x10cded8;
static const U cl_adc_record=0x10cd734,cl_vertical_record=0x1151638;
#endif
