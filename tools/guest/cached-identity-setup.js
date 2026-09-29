// Disposable ART setup only. The external reader runs after this script is unloaded and detached.
'use strict';
const cachedIdentityKeepalive = [];
function cachedSetupArtifact(name, bytes) {
    const payload = {kind:'cached-setup-artifact',sequence:++sequence,call:currentCall,
        name:name,size:bytes.byteLength,sha256:Checksum.compute('sha256',bytes)};
    journal.write(JSON.stringify(payload)+'\n');journal.flush();send(payload,bytes);
}
function cachedSetupRestoration(mod) {
    const rxSize=0xb69000;
    const base=Number(mod.base.toString());
    if(!Number.isSafeInteger(base)||Process.pageSize!==4096)throw new Error('Unexpected mapping arithmetic');
    let mapCheckpoint=0;
    function mappings() {
        const input=new File('/proc/self/maps','r');let text;
        try{text=input.readText(1024*1024+1);}finally{input.close();}
        if(text.length>=1024*1024)throw new Error('Setup maps evidence exceeded bound');
        cachedSetupArtifact('raw-maps-'+(++mapCheckpoint)+'.txt',
            Memory.allocUtf8String(text).readByteArray(text.length));
        const rows=[],lines=[];
        text.split('\n').forEach(line=>{
            const match=/^([0-9a-f]+)-([0-9a-f]+) ([rwxps-]{4}) ([0-9a-f]+) ([0-9a-f]+:[0-9a-f]+) ([0-9]+)\s*(.*)$/.exec(line);
            if(!match){if(line.length)throw new Error('Malformed setup maps row');return;}
            if(match[7]!==mod.path)return;
            const lo=parseInt(match[1],16),hi=parseInt(match[2],16),off=parseInt(match[4],16);
            if(!Number.isSafeInteger(lo)||!Number.isSafeInteger(hi)||lo<base||hi<=lo||lo%4096||hi%4096||off%4096)
                throw new Error('Unexpected setup library map alignment: '+line+' base='+mod.base.toString()+
                    ' lo='+lo+' hi='+hi+' off='+off);
            rows.push({start_offset:lo-base,end_offset:hi-base,file_offset:off,protection:match[3],
                device:match[5],inode:match[6],path:match[7]});lines.push(line);
        });
        if(!rows.length)throw new Error('No setup library mappings');
        const normalized=[];
        rows.forEach(row=>{
            const previous=normalized[normalized.length-1];
            if(previous&&previous.end_offset>row.start_offset)throw new Error('Overlapping setup mappings');
            if(previous&&previous.end_offset===row.start_offset&&previous.protection===row.protection&&
                previous.device===row.device&&previous.inode===row.inode&&previous.path===row.path&&
                previous.file_offset+previous.end_offset-previous.start_offset===row.file_offset)
                previous.end_offset=row.end_offset;
            else normalized.push(Object.assign({},row));
        });
        return {rows:rows,normalized:normalized,text:lines.join('\n')+'\n'};
    }
    function artifactMaps(name,snapshot) {
        const bytes=Memory.allocUtf8String(snapshot.text).readByteArray(snapshot.text.length);
        cachedSetupArtifact(name,bytes);
    }
    const original=mappings();
    const expected=[[0,0xb69000,0,'r-xp'],[0xb69000,0xb8f000,0xb68000,'r--p'],
        [0xb8f000,0xbe1000,0xb8e000,'rw-p']];
    if(original.normalized.length!==expected.length)throw new Error('Unexpected original library map count');
    original.normalized.forEach((row,i)=>{
        const e=expected[i];
        if(row.start_offset!==e[0]||row.end_offset!==e[1]||row.file_offset!==e[2]||row.protection!==e[3]||
            row.device!==original.rows[0].device||row.inode!==original.rows[0].inode||row.inode==='0')
            throw new Error('Original library mappings differ from pinned ELF/RELRO geometry');
    });
    const originalBytes=mod.base.readByteArray(rxSize);
    const originalHash=Checksum.compute('sha256',originalBytes);
    artifactMaps('maps-before.txt',original);cachedSetupArtifact('rx-before.bin',originalBytes);
    event('setup-mapping-baseline',{module_base:mod.base.toString(),module_path:mod.path,
        rx_size:rxSize,rx_sha256:originalHash,mappings:original.normalized});
    function eachPage(snapshot,fn) {
        snapshot.rows.forEach(row=>{
            for(let offset=row.start_offset;offset<row.end_offset;offset+=4096)
                fn(offset,Object.assign({},row,{start_offset:offset,end_offset:offset+4096,
                    file_offset:row.file_offset+offset-row.start_offset}));
        });
    }
    const originalPages=new Map();eachPage(original,(offset,row)=>originalPages.set(offset,row));
    return function restore(dnaAddress) {
        // All stock calls have returned. Remove every owned observer before restoring code protections.
        const count=listeners.length;
        listeners.splice(0).forEach(listener=>listener.detach());
        Interceptor.revert(dnaAddress);Interceptor.flush();
        event('setup-hooks-removed',{listeners_detached:count,dna_reverted:true,interceptor_flushed:true});
        const middle=mappings();artifactMaps('maps-after-hooks-removed.txt',middle);
        const restoredBytes=mod.base.readByteArray(rxSize);
        cachedSetupArtifact('rx-after-hooks-removed.bin',restoredBytes);
        const before=new Uint8Array(originalBytes),after=new Uint8Array(restoredBytes);
        for(let i=0;i<rxSize;i++)if(before[i]!==after[i])throw new Error('Original RX byte not restored at '+i.toString(16));
        event('setup-code-bytes-restored',{size:rxSize,sha256:Checksum.compute('sha256',restoredBytes),equal:true});
        const changed=[];let pages=0;
        eachPage(middle,(offset,row)=>{
            ++pages;const wanted=originalPages.get(offset);
            if(!wanted)throw new Error('Unexpected setup library mapping coverage');
            for(const field of ['start_offset','end_offset','file_offset','device','inode','path'])
                if(row[field]!==wanted[field])throw new Error('Setup mapping geometry/identity changed: '+field);
            if(row.protection!==wanted.protection) {
                if(wanted.protection!=='r-xp'||row.protection!=='rwxp')throw new Error('Unexpected setup protection delta');
                changed.push(offset);
            }
        });
        if(pages!==originalPages.size)throw new Error('Setup mapping page coverage changed');
        changed.forEach(offset=>{
            const address=mod.base.add(offset);
            event('setup-page-protection-restored',{address:address.toString(),module_offset:offset,size:4096,
                before:'rwx',after:'r-x',phase:'setup',operation:'Memory.protect'});
            if(!Memory.protect(address,4096,'r-x'))throw new Error('Setup RX protection restoration failed');
        });
        const final=mappings();artifactMaps('maps-restored.txt',final);
        if(JSON.stringify(final.normalized)!==JSON.stringify(original.normalized))
            throw new Error('Setup library mappings not restored exactly');
        event('setup-mapping-restoration-complete',{mappings_equal:true,code_bytes_equal:true,
            rx_sha256:originalHash,restored_pages:changed.length,mappings:final.normalized});
    };
}

function entitlementExperiment() {
    try {
        const mod = aukletModule;
        if (mod === null || Process.arch !== 'arm64') throw new Error('Actual ART/Auklet unavailable');
        const restoreSetup = cachedSetupRestoration(mod);
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
        restoreSetup(requiredExport(name,'_Z21Drv_System_GetFPGADNARy'));
        event('cached-identity-ready',{pid:Process.id,module_base:mod.base.toString(),module_path:mod.path,
            expected_dna_hex:dnaHex,expected_file_keys_hex:keyHex,expected_sample_hex:dnaHex+keyHex,
            dna_elf_va:'0xbbccf0',file_keys_elf_va:'0xbbcd1c',started_false:true,stock_calls_complete:true,
            stock_native_sha256:STOCK_AUKLET_SHA256,synthetic_only:true,physical_contact:false,
            setup_restoration_complete:true});
        recv('cached-identity-ack',function(){}).wait();
        event('cached-identity-setup-returned',{pid:Process.id,target_left_alive:true,no_further_stock_calls:true});
        journal.close();
    } catch(error) {
        stop('failure','cached-identity-setup-error',78,Object.assign({message:String(error)},faultDetails(error)));
    }
}
