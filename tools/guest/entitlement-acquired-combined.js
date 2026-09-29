// Composed with the pinned ART and baseline helpers. Acquired inputs are private; guest private storage is modeled.
// Only the FPGA DNA data response is modeled; stock license parsing/validation stays intact.
'use strict';
const entitlementAcquiredCombinedKeepalive = [];

function entitlementExperiment() {
    try {
        const cfg = entitlementFixture;
        const phase = entitlementPhase;
        const checkpoint = entitlementCheckpoint;
        const expectedSeeds = [[5,'FlexA'],[24,'BWU05T08'],[29,'AFG100'],[30,'AFG50'],[6,'AUDIOA'],[4,'AUTOA'],[7,'AEROA'],[19,'RLU05'],[22,'BWU03T05'],[23,'BWU03T08']];
        const derivedPin = '09689a442e8d285775b37089a8d631e1e445fe03d3499e830cdcc8f32439504e';
        const expectedPin = cfg.capability_arm === 'derived' ? derivedPin : STOCK_AUKLET_SHA256;
        if (cfg.schema_version !== 'mho900-lab.acquired-option-fixture/1' ||
            cfg.acquired_combined_experiment !== true || cfg.acquired_option_experiment !== true ||
            cfg.capability_experiment !== true || !['stock','derived'].includes(cfg.capability_arm) ||
            cfg.acquired_catalog_experiment === true || cfg.acquired_capability_experiment === true ||
            cfg.catalog_candidate !== undefined || cfg.option_type !== undefined ||
            phase !== 'reload' || !/^[a-z0-9-]{1,40}$/.test(checkpoint) ||
            cfg.stock_native_sha256 !== STOCK_AUKLET_SHA256 || cfg.expected_native_sha256 !== expectedPin ||
            cfg.token_text_encoding !== 'low-nibble-first' || cfg.consumer_observation_required !== true ||
            cfg.model !== 'MHO984' || cfg.license_type !== 0 || cfg.license_time !== 0 ||
            cfg.aes_key_ascii.length !== 32 || cfg.key_field_hex.length !== 260 || cfg.key_ciphertext_hex.length !== 296 ||
            cfg.physical_contact !== false || cfg.specimen_key_files_used !== true ||
            !Array.isArray(cfg.seed_files) || cfg.seed_files.length !== 22 || !Array.isArray(cfg.seed_catalog) ||
            !Array.isArray(cfg.seed_options) || cfg.seed_options.length !== expectedSeeds.length ||
            !cfg.seed_options.every((x,i)=>x.type===expectedSeeds[i][0]&&x.name===expectedSeeds[i][1]&&x.padded_bytes===48))
            throw new Error('Unexpected acquired combined fixture');
        const capabilityCfg = cfg;
        const mod = aukletModule;
        if (mod === null || Process.arch !== 'arm64') throw new Error('ART/Auklet not ready');
        const nm = mod.name;
        const capability = entitlementCapabilityPrepare(mod, capabilityCfg, event, invoke);
        let capabilityChecks = null;
        if (typeof entitlementObserveConsumer !== 'function') throw new Error('Required consumer observer missing');
        entitlementObserveConsumer(mod, event, cfg);
        event('entitlement-phase-start', { phase: phase, identity: 'acquired-fixture', model: cfg.model,
            serial: cfg.serial, dna_hex: cfg.dna_hex, stock_files_unchanged: expectedPin === STOCK_AUKLET_SHA256, acquired_combined_experiment: true,
            stock_apk_unchanged: true, native_library_derived: expectedPin !== STOCK_AUKLET_SHA256 });
        function fn(name, result, args) { return native(nm, name, result, args); }
        function guarded(va, bytes, result, args) {
            return checkedLocalFunction(mod, va, bytes, result, args);
        }
        function call(label, f, args) { return invoke(label, f, args); }
        function bytes(p, n) { return Array.from(new Uint8Array(p.readByteArray(n))); }
        function hex(arr) { return arr.map(x => ('0' + x.toString(16)).slice(-2)).join(''); }
        function equal(a, b) { return hex(a) === hex(b); }
        function ascii(text) {
            if (!/^[\x20-\x7e]+$/.test(text)) throw new Error('Non-ASCII fixture');
            return Array.from(text, c => c.charCodeAt(0));
        }
        const ctor = guarded(0x239014, 'ff8300d1fd7b01a9fd430091e00700f9', 'void', ['pointer', 'pointer']);
        const dtor = guarded(0x239040, 'ff8300d1fd7b01a9fd430091e00700f9', 'void', ['pointer']);
        const cstr = guarded(0x235978, 'ff8300d1fd7b01a9fd430091e00700f9e00740f90a000094', 'pointer', ['pointer']);
        function withString(text, label, action) {
            const obj = Memory.alloc(24);
            call('RString::ctor:' + label, ctor, [obj, Memory.allocUtf8String(text)]);
            try { return action(obj); } finally { call('RString::dtor:' + label, dtor, [obj]); }
        }
        const open = new SystemFunction(requiredExport('libc.so', 'open'), 'int', ['pointer', 'int', 'int']);
        const read = native('libc.so', 'read', 'long', ['int', 'pointer', 'ulong']);
        const close = native('libc.so', 'close', 'int', ['int']);
        function readFile(path, optional) {
            const opened = call('open-read:' + path, open, [Memory.allocUtf8String(path), 0, 0]);
            if (opened.value < 0) {
                if (optional && opened.errno === 2) return null;
                throw new Error('Read open failed ' + path + ' errno=' + opened.errno);
            }
            const fd = opened.value;
            const buf = Memory.alloc(4096);
            const data = [];
            try {
                for (;;) {
                    const n = Number(call('read:' + path, read, [fd, buf, 4096]));
                    if (n < 0) throw new Error('Read failed ' + path);
                    if (n === 0) break;
                    data.push.apply(data, bytes(buf, n));
                    if (data.length > 65536) throw new Error('Unexpected fixture file size');
                }
            } finally { if (call('close-read:' + path, close, [fd]) !== 0) throw new Error('Close failed'); }
            return data;
        }
        ['Dev_PCIeInit', '_ZN9CApiSetup11loadPrivacyEv', '_ZN11CApiLicense28ApiLicense_SetLicenseInstallE7RString', 'AES_encrypt', '_ZN6CXXTEA6encodeEPil'].forEach(name =>
            observeStop(requiredExport(nm, name), 'unexpected-physical-dependency:' + name));
        const verifyReturns = [], errorCodes = [];
        const verifyAddress = requiredExport(nm, '_ZN11CApiLicense12verifyOptionEP8COptInfoR7RStringS3_');
        listeners.push(Interceptor.attach(verifyAddress, {
            onEnter(args) { this.optionType = args[1].readS32(); this.scope = currentCall; event('stock-verify-enter', {option_type: this.optionType, consumer_call: this.scope}); },
            onLeave(ret) { const valid = (ret.toInt32() & 1) !== 0; verifyReturns.push({option_type: this.optionType, consumer_call: this.scope, valid: valid}); event('stock-verify-return', {option_type: this.optionType, consumer_call: this.scope, valid: valid}); }
        }));
        listeners.push(Interceptor.attach(requiredExport(nm, '_ZN8CApiCore9syncErrorEi'), {
            onEnter(args) { const code = args[0].toInt32(); errorCodes.push(code); event('stock-sync-error', { stock_code: code }); }
        }));
        listeners.push(Interceptor.attach(requiredExport(nm, '_Z14JNI_SetErrCodeiii'), {
            onEnter(args) { event('stock-result-notification', { service_id: args[0].toInt32(), message_id: args[1].toInt32(), stock_code: args[2].toInt32(), original_retained: true }); }
        }));
        const started = guarded(0x241fb4, '684a00d008210091090140392a008052', 'bool', []);
        if (call('API_GetStarted:preflight', started)) throw new Error('Unexpected started component requires Activity');
        const dnaAddress = requiredExport(nm, '_Z21Drv_System_GetFPGADNARy');
        guarded(0x2f18f8, 'ff8300d1fd7b01a9fd43009108008052', 'int', ['pointer']);
        const dnaResponse = new NativeCallback(function (out) {
            out.writeU64(uint64('0x' + cfg.dna_hex));
            event('synthetic-dna-response', { dna_hex: cfg.dna_hex, status: 0 });
            return 0;
        }, 'int', ['pointer']);
        entitlementAcquiredCombinedKeepalive.push(dnaResponse);
        Interceptor.replace(dnaAddress, dnaResponse);
        Interceptor.flush();
        const store = globalThis.entitlementPrivateStore.create(mod, event, invoke);
        store.preflight();
        observeFactory(mod);
        if (call('CApiFactory::Api_Create', fn('_ZN11CApiFactory10Api_CreateEv', 'int', [])) !== 0) throw new Error('Api_Create failed');
        const services = call('getServiceList', fn('_ZN11CApiFactory14getServiceListEv', 'pointer', []));
        const size = guarded(0x238f64, 'ff4300d1080180d2e00700f9e90740f92a0540f9290140f9', 'ulong', ['pointer']);
        const count = Number(call('stock-vector::size', size, [services]));
        if (count !== 49) throw new Error('Expected 49 stock services, got ' + count);
        const at = fn('_ZNSt6__ndk16vectorIP8CApiBaseNS_9allocatorIS2_EEE2atEm', 'pointer', ['pointer', 'ulong']);
        const getId = fn('_ZNK8CApiBase5getIdEv', 'int', ['pointer']);
        const ids = [];
        for (let i = 0; i < count; i++) {
            const base = call('service-at:' + i, at, [services, i]).readPointer();
            ids.push(call('service-id:' + i, getId, [base]));
        }
        event('service-inventory-complete', { count: count, service_ids: ids });
        const executor = guarded(0x263130, 'ff0301d1fd7b03a9fdc30091080080d2', 'pointer', ['int']);
        const license = call('getExecutor:36', executor, [36]);
        const utility = call('getExecutor:11', executor, [11]);
        if (license.isNull() || utility.isNull()) throw new Error('Stock executor missing');
        withString(cfg.model, 'synthetic-model', obj => {
            const selected = call('ApiUtility_SetModel', guarded(0x429d48, 'ff8304d1fc8300f9fd7b11a9fd430491', 'pointer', ['pointer']), [obj]);
            if (selected.isNull()) throw new Error('Model selection failed');
            // SetModel returns row+0x40 c_str; only the observed ParseModel return identifies the row.
            event('stock-model-setter-return', { pointer: selected.toString(), interpretation: 'selected-row-extra-field-c-string' });
        });
        if (capability !== null) capability.selectedRecord();
        withString(cfg.serial, 'synthetic-serial', obj => {
            if (call('ApiUtility_SetSerial', guarded(0x4244fc, 'ff8300d1fd7b01a9fd430091483b00b0', 'int', ['pointer']), [obj]) !== 0) throw new Error('Serial setter failed');
        });
        const observedModel = call('cached-model', cstr, [requiredExport(nm, '_ZN11CApiUtility14strStaticModelE')]).readUtf8String();
        const observedSerial = call('cached-serial', cstr, [requiredExport(nm, '_ZN11CApiUtility15strStaticSerialE')]).readUtf8String();
        if (observedModel !== cfg.model || observedSerial !== cfg.serial) throw new Error('Identity setter roundtrip differs');
        const rawBandwidth = mod.base.add(0xbbcce4).readS32();
        const systemBandwidth = mod.base.add(0xbbcce8).readS32();
        event('synthetic-model-capability', { model: observedModel, raw_bandwidth_enum: rawBandwidth, system_bandwidth_enum: systemBandwidth });
        const expectedBandwidth = capabilityCfg.expected_bandwidth_enum;
        if (rawBandwidth !== expectedBandwidth || systemBandwidth !== expectedBandwidth) throw new Error('Unexpected stock MHO984 bandwidth');
        call('ApiUtility_GetDNA', guarded(0x42a7dc, 'ff0302d1fd7b07a9fdc3019148d03bd5', 'void', []));
        const actualDna = requiredExport(nm, '_ZN11CApiUtility5m_DNAE').readU64();
        if (actualDna.compare(uint64('0x' + cfg.dna_hex)) !== 0) throw new Error('Stock DNA side effect differs');
        const fileKeys = requiredExport(nm, 'fileKeys');
        call('ApiUtility_ConvertDNA2Key', guarded(0x42a91c, 'ff8300d1fd7b01a9fd430091083b00f0', 'void', ['pointer']), [fileKeys]);
        event('synthetic-identity-confirmed', { model: observedModel, serial: observedSerial, dna_hex: cfg.dna_hex,
            file_keys_hex: hex(bytes(fileKeys, 16)), acquired_material: true });
        if (hex(bytes(fileKeys,16)) !== cfg.file_keys_hex) throw new Error('Acquired file keys differ');
        function guestPath(relative) {
            if (/^rigol\/data\/[A-Za-z0-9.-]+$/.test(relative)) return '/' + relative;
            if (/^model\/[A-Za-z0-9.-]+$/.test(relative)) return '/data/local/tmp/entitlement/' + relative;
            throw new Error('Unexpected seed path');
        }
        const seeded = cfg.seed_files.map(item => {
            if (!/^[a-f0-9]{64}$/.test(item.sha256)) throw new Error('Missing seed hash');
            return {path: item.path, sha256_expected: item.sha256, data: readFile(guestPath(item.path), false)};
        });
        if (!seeded.some(x => x.path === 'rigol/data/Key.data') ||
            !seeded.some(x => x.path === 'model/private.mem')) throw new Error('Incomplete seed inventory');
        function optionFile(item) {
            if (!/^[A-Za-z0-9]+$/.test(item.name) || ![32,48].includes(item.padded_bytes) ||
                !new RegExp('^[a-f0-9]{' + (item.padded_bytes * 2) + '}$').test(item.wire_token_hex) ||
                item.wire_token_hex !== item.token_ciphertext_hex.replace(/../g, pair => pair[1] + pair[0])) throw new Error('Malformed seeded option');
            const path = '/rigol/data/' + item.name + '.lic';
            const content = readFile(path, false);
            if (String.fromCharCode.apply(null, content).trim() !== item.name + '@' + item.wire_token_hex) throw new Error('Seed license differs: ' + item.name);
            return content;
        }
        cfg.seed_options.forEach(optionFile);
        event('catalog-seed-inputs', {files: seeded.map(x => ({path:x.path, size:x.data.length, sha256_expected:x.sha256_expected})),
            options: cfg.seed_options, private_backend:'stock-memfile-harness-directed-file'});
        const keyOutputs = [];
        const countString = guarded(0x23df40, 'ffc300d1fd7b02a9fd830091a0831ff8', 'ulong', ['pointer']);
        listeners.push(Interceptor.attach(requiredExport(nm, '_ZN11CApiLicense13getLicenseKeyER7RStringS1_'), {
            onEnter(args) { this.key = args[1]; this.left = args[2]; },
            onLeave() {
                const n = Number(countString(this.key));
                if (n !== 130) { stop('failure','acquired-key-length',78,{}); return; }
                const value = {};
                value.key_hex = hex(bytes(cstr(this.key),n));
                value.left_field = cstr(this.left).readUtf8String();
                keyOutputs.push(value); event('acquired-key-outputs',value);
            }
        }));
        store.initialize('reload');
        call('CApiLicense::init', fn('_ZN11CApiLicense4initEv','void',['pointer']),[license]);
        if (keyOutputs.length !== 1 || keyOutputs[0].key_hex !== cfg.key_field_hex || keyOutputs[0].left_field !== cfg.key_left) throw new Error('Acquired parser outputs differ');
        store.snapshot(checkpoint+'-before');
        const catalog=[[0,'BND'],[1,'EMBD'],[2,'COMP'],[3,'AUTO'],[4,'AUTOA'],[5,'FlexA'],[6,'AUDIOA'],[7,'AEROA'],[19,'RLU05'],[30,'AFG50'],[29,'AFG100'],[22,'BWU03T05'],[23,'BWU03T08'],[24,'BWU05T08']];
        const query=fn('_ZN11CApiLicense26ApiLicense_GetLicenseValidE7OptTypeRb','int',['pointer','int','pointer']);
        function queryAll(label) {
            const out=Memory.alloc(1);
            const result=catalog.map(item=>{out.writeU8(0);const status=call('GetLicenseValid:'+label+':'+item[1],query,[license,item[0],out]);
                if(status!==0)throw new Error('Catalog query failed');
                return{option_type:item[0],option_name:item[1],valid:out.readU8()!==0,status:status};});
            event('option-catalog',{phase:phase,checkpoint:label,options:result});return result;
        }
        function catalogEqual(actual,expected) {
            return actual.length===14&&expected.length===14&&actual.every((x,i)=>x.option_type===expected[i].option_type&&
                x.option_name===expected[i].option_name&&x.valid===expected[i].valid&&x.status===expected[i].status);
        }
        const before=queryAll('before');
        if(!catalogEqual(before,cfg.seed_catalog))throw new Error('Seed catalog mismatch');
        capabilityChecks=capability.evaluate(utility);
        const after=queryAll('after');
        store.snapshot(checkpoint+'-after');
        const preserved=seeded.every(x=>equal(readFile(guestPath(x.path),false),x.data));
        const checks={started_false:!call('API_GetStarted:final',started),catalog_complete:before.length===14&&after.length===14,
            seed_catalog_matches:catalogEqual(before,cfg.seed_catalog),seed_inputs_preserved:preserved,private_reloaded:true,
            catalog_unchanged:catalogEqual(after,cfg.seed_catalog),no_installer:true,no_token_regeneration:true};
        Object.assign(checks,capabilityChecks);
        const details={phase:phase,acquired_combined_experiment:true,expected_checks:checks,
            catalog_before:before,catalog_after:after,verify_returns:verifyReturns,stock_codes:errorCodes,
            persistence_backend:'stock-memfile-harness-directed-file',physical_contact:false};
        event('entitlement-phase-evaluation',details);
        if(!Object.keys(checks).every(k=>checks[k]===true)){stop('failure','entitlement-phase-expectation-mismatch',78,details);return;}
        stop('dependency-stop','acquired-combined-phase-complete',77,details);
    } catch(error) {
        stop('failure','entitlement-combined-error',78,Object.assign({phase:entitlementPhase,message:String(error)},faultDetails(error)));
    }
}
