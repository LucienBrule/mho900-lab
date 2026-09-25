#ifndef MHO_ADC_PARAMETER_CAPTURE_H
#define MHO_ADC_PARAMETER_CAPTURE_H
#define ADCI_FILES 9U
#define ADCI_BINDINGS 16U
#define ADCI_MAP_MAX 2048U
#define ADCI_MAP_BYTES 262144U
#define ADCI_RAW_MAX 16384U
static const U adci_length[ADCI_FILES]={0xe60,0x1c71,0x10,0x12c,0x3c,8,0x3c,0x74,0x2c};
static const char *const adci_file[ADCI_FILES]={"adc-input-matrix.bin","adc-input-setting.bin","adc-input-drvparam.bin","adc-input-series.bin","adc-input-config.bin","adc-input-sample-entry.bin","adc-input-shadow-low.bin","adc-input-shadow-high.bin","adc-input-global-inputs.bin"};
static const U adci_slot[ADCI_BINDINGS]={0xb8eea8,0xb8cb08,0xb8c9d0,0xb8b940,0xb8cae0,0xb8ec98,0xb8e680,0xb8da70,0xb8d288,0xb8de88,0xb8ed38,0xb8dd30,0xb8db70,0xb8d5b8,0xb8ddc0,0xb8ccd8};
static const U adci_target[ADCI_BINDINGS]={0x9948bc,0x3cb45bc,0x3cb45a6,0x3cb457c,0x3cb45b8,0x3cb45ec,0x3cb45d8,0x3cb4534,0x3cb44fc,0xbe1138,0xbe1144,0xbe113c,0xbe1148,0xbe1140,0xbe114c,0xbe1150};
static const U adci_width[ADCI_BINDINGS]={312,4,16,16,4,4,4,4,4,4,4,4,4,4,4,4};
static const U adci_table_target[9]={0xb8f808,0xb8f808,0xb8f808,0xb8f908,0xb8fa08,0xb8fb08,0xb8fc08,0xb8fc08,0xb8fc08};
static const U adci_config_target[9]={0xb8f40c,0xb8f40c,0xb8f478,0xb8f2c8,0xb8f3a0,0xb8f40c,0,0,0};
#endif
