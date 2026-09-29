// Disposable ART setup only. The external reader runs after this script is unloaded and detached.
'use strict';
const cachedIdentityKeepalive = [];
function entitlementExperiment() {
    try {
        const mod = aukletModule;
        if (mod === null || Process.arch !== 'arm64') throw new Error('Actual ART/Auklet unavailable');
        const name = mod.name;
        const guarded = (va, bytes, result, args) => checkedLocalFunction(mod, va, bytes, result, args);
        const started = guarded(0x241fb4, '684a00d008210091090140392a008052', 'bool', []);
        const ctor = guarded(0x239014, 'ff8300d1fd7b01a9fd430091e00700f9', 'void', ['pointer','pointer']);
        const dtor = guarded(0x239040, 'ff8300d1fd7b01a9fd430091e00700f9', 'void', ['pointer']);
        const setModel = guarded(0x429d48, 'ff8304d1fc8300f9fd7b11a9fd430491', 'pointer', ['pointer']);
        const setSerial = guarded(0x4244fc, 'ff8300d1fd7b01a9fd430091483b00b0', 'int', ['pointer']);
        const getDna = guarded(0x42a7dc, 'ff0302d1fd7b07a9fdc3019148d03bd5', 'void', []);
        const convert = guarded(0x42a91c, 'ff8300d1fd7b01a9fd430091083b00f0', 'void', ['pointer']);
        guarded(0x2f18f8, 'ff8300d1fd7b01a9fd43009108008052', 'int', ['pointer']);
        const vectorSize = guarded(0x238f64, 'ff4300d1080180d2e00700f9e90740f92a0540f9290140f9', 'ulong', ['pointer']);
        ['Dev_PCIeInit','_ZN9CApiSetup11loadPrivacyEv','_ZN11CApiLicense4initEv',
            '_ZN11CApiLicense28ApiLicense_SetLicenseInstallE7RString'].forEach(symbol =>
                observeStop(requiredExport(name,symbol),'unexpected-cached-setup-dependency:'+symbol));
        if (invoke('API_GetStarted:preflight',started)) throw new Error('Component already started');
        const syntheticDna='0123456789abcdef';
        const dnaResponse=new NativeCallback(function(out) {
            out.writeU64(uint64('0x'+syntheticDna));
            event('synthetic-dna-response',{dna_hex:syntheticDna,status:0});return 0;
        },'int',['pointer']);
        cachedIdentityKeepalive.push(dnaResponse);
        Interceptor.replace(requiredExport(name,'_Z21Drv_System_GetFPGADNARy'),dnaResponse);
        Interceptor.flush();
        observeFactory(mod);
        if(invoke('CApiFactory::Api_Create',native(name,'_ZN11CApiFactory10Api_CreateEv','int',[]))!==0)throw new Error('Factory failed');
        const services=invoke('getServiceList',native(name,'_ZN11CApiFactory14getServiceListEv','pointer',[]));
        const count=Number(invoke('stock-vector::size',vectorSize,[services]));
        if(count!==49)throw new Error('Unexpected service count');
        event('service-inventory-complete',{count:count});
        function withString(text,label,fn) {
            const obj=Memory.alloc(24);invoke('RString::ctor:'+label,ctor,[obj,Memory.allocUtf8String(text)]);
            try{return fn(obj);}finally{invoke('RString::dtor:'+label,dtor,[obj]);}
        }
        withString('MHO984','synthetic-model',obj=>{
            if(invoke('ApiUtility_SetModel',setModel,[obj]).isNull())throw new Error('Model setter failed');
        });
        withString('SYNTH01','synthetic-serial',obj=>{
            if(invoke('ApiUtility_SetSerial',setSerial,[obj])!==0)throw new Error('Serial setter failed');
        });
        invoke('ApiUtility_GetDNA',getDna);
        const dna=requiredExport(name,'_ZN11CApiUtility5m_DNAE'),keys=requiredExport(name,'fileKeys');
        if(!dna.equals(mod.base.add(0xbbccf0))||!keys.equals(mod.base.add(0xbbcd1c)))throw new Error('Cached symbol address differs');
        invoke('ApiUtility_ConvertDNA2Key',convert,[keys]);
        function hex(address,n){return Array.from(new Uint8Array(address.readByteArray(n)),b=>('0'+b.toString(16)).slice(-2)).join('');}
        const dnaHex=hex(dna,8),keyHex=hex(keys,16);
        if(dnaHex!=='efcdab8967452301')throw new Error('Synthetic DNA byte order differs');
        if(invoke('API_GetStarted:final',started))throw new Error('Setup started business');
        event('cached-identity-ready',{pid:Process.id,module_base:mod.base.toString(),module_path:mod.path,
            expected_dna_hex:dnaHex,expected_file_keys_hex:keyHex,expected_sample_hex:dnaHex+keyHex,
            dna_elf_va:'0xbbccf0',file_keys_elf_va:'0xbbcd1c',started_false:true,stock_calls_complete:true,
            stock_native_sha256:STOCK_AUKLET_SHA256,synthetic_only:true,physical_contact:false});
        recv('cached-identity-ack',function(){}).wait();
        event('cached-identity-setup-returned',{pid:Process.id,target_left_alive:true,no_further_stock_calls:true});
        journal.close();
    } catch(error) {
        stop('failure','cached-identity-setup-error',78,Object.assign({message:String(error)},faultDetails(error)));
    }
}
