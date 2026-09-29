// Composed with the pinned ART and baseline helpers. All personality inputs are synthetic.
// Only the FPGA DNA data response is modeled; stock license parsing/validation stays intact.
'use strict';
const entitlementCatalogKeepalive = [];

function entitlementExperiment() {
    try {
        const cfg = entitlementFixture;
        const phase = entitlementPhase;
        const checkpoint = entitlementCheckpoint;
        const candidate = cfg.catalog_candidate;
        const allowed = [[24,'BWU05T08',48],[29,'AFG100',32],[30,'AFG50',32],[6,'AUDIOA',32],
            [4,'AUTOA',32],[7,'AEROA',32],[19,'RLU05',32],[22,'BWU03T05',48],[23,'BWU03T08',48]];
        if (cfg.catalog_experiment !== true || !['negative', 'positive', 'reload'].includes(phase) ||
            !/^[a-z0-9-]{1,40}$/.test(checkpoint) || !candidate ||
            !allowed.some(x => x[0] === candidate.type && x[1] === candidate.name && x[2] === candidate.padded_bytes) ||
            cfg.stock_native_sha256 !== STOCK_AUKLET_SHA256 || cfg.expected_native_sha256 !== STOCK_AUKLET_SHA256 ||
            cfg.token_text_encoding !== 'low-nibble-first' || cfg.consumer_observation_required !== true ||
            cfg.model !== 'MHO984' || cfg.serial !== 'SYNTH01' || cfg.license_type !== 0 || cfg.license_time !== 0 ||
            cfg.aes_key_ascii !== '0123456789abcdef0123456789abcdef' || cfg.physical_contact !== false ||
            cfg.specimen_key_files_used !== false || !Array.isArray(cfg.seed_options) ||
            !Array.isArray(cfg.seed_files) || !Array.isArray(cfg.seed_catalog)) throw new Error('Unexpected catalog fixture');
        const capabilityCfg = Object.assign({}, cfg, {capability_experiment: true, capability_arm: 'stock',
            expected_bandwidth_enum: 17, expected_record_offset: '0x151b7a0'});
        const mod = aukletModule;
        if (mod === null || Process.arch !== 'arm64') throw new Error('ART/Auklet not ready');
        const nm = mod.name;
        const capability = entitlementCapabilityPrepare(mod, capabilityCfg, event, invoke);
        let capabilityChecks = null;
        // Check original bytes before the consumer observer patches this entry for observation.
        const stockDecode = guarded(0x242fe8, 'ff0301d1fd7b03a9fdc30091a1831ff8', 'void', ['pointer', 'pointer', 'pointer']);
        if (typeof entitlementObserveConsumer !== 'function') throw new Error('Required consumer observer missing');
        entitlementObserveConsumer(mod, event, cfg);
        event('entitlement-phase-start', { phase: phase, identity: 'synthetic', model: cfg.model,
            serial: cfg.serial, dna_hex: cfg.dna_hex, stock_files_unchanged: true, catalog_experiment: true,
            stock_apk_unchanged: true, native_library_derived: false });
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
        const write = native('libc.so', 'write', 'long', ['int', 'pointer', 'ulong']);
        const close = native('libc.so', 'close', 'int', ['int']);
        const fsync = native('libc.so', 'fsync', 'int', ['int']);
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
        function writeFile(path, data) {
            const opened = call('open-write:' + path, open, [Memory.allocUtf8String(path), 0xc1, 0x180]);
            if (opened.value < 0) throw new Error('Write open failed errno=' + opened.errno);
            const fd = opened.value;
            const p = Memory.alloc(data.length);
            p.writeByteArray(data);
            try {
                let offset = 0;
                while (offset < data.length) {
                    const n = Number(call('write:' + path, write, [fd, p.add(offset), data.length - offset]));
                    if (n <= 0) throw new Error('Write failed');
                    offset += n;
                }
                if (call('fsync:' + path, fsync, [fd]) !== 0) throw new Error('fsync failed');
            } finally { if (call('close-write:' + path, close, [fd]) !== 0) throw new Error('Close failed'); }
            if (!equal(readFile(path, false), data)) throw new Error('Write readback differs');
        }
        ['Dev_PCIeInit', '_ZN9CApiSetup11loadPrivacyEv'].forEach(name =>
            observeStop(requiredExport(nm, name), 'unexpected-physical-dependency:' + name));
        const activeReturns = [], verifyReturns = [], errorCodes = [];
        const activeAddress = requiredExport(nm, '_ZN11CApiLicense9activeOptE7OptTypeR7RString');
        const verifyAddress = requiredExport(nm, '_ZN11CApiLicense12verifyOptionEP8COptInfoR7RStringS3_');
        listeners.push(Interceptor.attach(activeAddress, {
            onEnter(args) { this.optionType = args[1].toInt32(); event('stock-active-enter', { option_type: this.optionType }); },
            onLeave(ret) { activeReturns.push(ret.toInt32()); event('stock-active-return', { option_type: this.optionType, result: ret.toInt32() }); }
        }));
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
        entitlementCatalogKeepalive.push(dnaResponse);
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
        const expectedBandwidth = 17;
        if (rawBandwidth !== expectedBandwidth || systemBandwidth !== expectedBandwidth) throw new Error('Unexpected stock MHO984 bandwidth');
        call('ApiUtility_GetDNA', guarded(0x42a7dc, 'ff0302d1fd7b07a9fdc3019148d03bd5', 'void', []));
        const actualDna = requiredExport(nm, '_ZN11CApiUtility5m_DNAE').readU64();
        if (actualDna.compare(uint64('0x' + cfg.dna_hex)) !== 0) throw new Error('Stock DNA side effect differs');
        const fileKeys = requiredExport(nm, 'fileKeys');
        call('ApiUtility_ConvertDNA2Key', guarded(0x42a91c, 'ff8300d1fd7b01a9fd430091083b00f0', 'void', ['pointer']), [fileKeys]);
        event('synthetic-identity-confirmed', { model: observedModel, serial: observedSerial, dna_hex: cfg.dna_hex,
            file_keys_hex: hex(bytes(fileKeys, 16)), acquired_material: false });
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
            !seeded.some(x => x.path === 'model/crypto-witness.toml') ||
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
        const candidatePath = '/rigol/data/' + candidate.name + '.lic';
        const witnessPath = '/data/local/tmp/entitlement/model/crypto-' + candidate.name + (phase === 'negative' ? '-negative' : '') + '.toml';
        let witness;
        if (phase === 'reload') {
            const text = String.fromCharCode.apply(null, readFile(witnessPath, false));
            const match = /^schema_version = 3\nphase = "positive"\noption_type = ([0-9]+)\noption_name = "([A-Za-z0-9]+)"\npadded_bytes = (32|48)\nplaintext = "([A-Za-z0-9#]+)"\ntoken_ciphertext_hex = "([a-f0-9]+)"\nwire_token_hex = "([a-f0-9]+)"\n$/.exec(text);
            if (!match || Number(match[1]) !== candidate.type || match[2] !== candidate.name ||
                Number(match[3]) !== candidate.padded_bytes || match[4] !== candidate.positive_plaintext) throw new Error('Candidate reload witness mismatch');
            witness = {phase:'positive', option_type:candidate.type, option_name:candidate.name,
                padded_bytes:candidate.padded_bytes, plaintext:match[4],token_ciphertext_hex:match[5],wire_token_hex:match[6],witness_path:witnessPath};
            optionFile({name:candidate.name,padded_bytes:candidate.padded_bytes,wire_token_hex:match[6],token_ciphertext_hex:match[5]});
            event('catalog-candidate-witness', Object.assign({},witness,{loaded:true,crypto_regenerated:false}));
        } else {
            if (readFile(candidatePath,true) !== null || readFile(witnessPath,true) !== null) throw new Error('Candidate already present');
            const padded = candidate.padded_bytes;
            const plaintext = phase === 'negative' ? candidate.negative_plaintext : candidate.positive_plaintext;
            const expectedPlaintext = 'MHO984#SYNTH01#' + (phase === 'negative' ? 'Wrong' : candidate.name) + '#guest#0#0';
            if (plaintext !== expectedPlaintext) throw new Error('Candidate plaintext differs');
            const plain = ascii(plaintext);
            if (plain.length >= padded) throw new Error('Candidate plaintext too long');
            while (plain.length < padded) plain.push(0);
            const encSchedule = Memory.alloc(256), decSchedule = Memory.alloc(256), aesKey = Memory.allocUtf8String(cfg.aes_key_ascii);
            const aesSet = guarded(0x3e9d24, 'ff4301d1fd7b04a9fd03019148d03bd5', 'int', ['pointer','int','pointer']);
            const aesEncrypt = guarded(0x3ea76c, 'ff4303d1fc6f07a9fa6708a9f85f09a9', 'void', ['pointer','pointer','pointer']);
            const aesDecSet = fn('AES_set_decrypt_key','int',['pointer','int','pointer']);
            const aesDecrypt = fn('AES_decrypt','void',['pointer','pointer','pointer']);
            if (call('AES_set_encrypt_key',aesSet,[aesKey,256,encSchedule]) !== 0 ||
                call('AES_set_decrypt_key',aesDecSet,[aesKey,256,decSchedule]) !== 0) throw new Error('AES schedule failed');
            const source=Memory.alloc(padded),cipher=Memory.alloc(padded),recovered=Memory.alloc(padded);
            source.writeByteArray(plain);
            for (let i=0;i<padded;i+=16) {
                call('AES_encrypt:block'+i,aesEncrypt,[source.add(i),cipher.add(i),encSchedule]);
                call('AES_decrypt:roundtrip'+i,aesDecrypt,[cipher.add(i),recovered.add(i),decSchedule]);
            }
            if (!equal(bytes(recovered,padded),plain)) throw new Error('AES roundtrip failed');
            const conventional=hex(bytes(cipher,padded)),wire=conventional.replace(/../g,pair=>pair[1]+pair[0]);
            function codecControl(text,encoding,predicted,expectedMatch) {
                const destination=Memory.alloc(padded),lengthOut=Memory.alloc(4); lengthOut.writeS32(-1);
                withString(text,'codec-'+encoding,obj=>call('API_SetStr2Hex:control:'+encoding,stockDecode,[obj,destination,lengthOut]));
                const length=lengthOut.readS32(); if(length!==padded) throw new Error('Decoder length differs');
                const decoded=hex(bytes(destination,length)),matches=decoded===conventional;
                event('synthetic-wire-codec-control',{input_encoding:encoding,input_text:text,decoded_hex:decoded,decoded_length:length,
                    expected_hex:conventional,predicted_decoded_hex:predicted,matches_prediction:decoded===predicted,matches_expected:matches});
                if(decoded!==predicted||matches!==expectedMatch) throw new Error('Decoder control failed');
            }
            codecControl(conventional,'conventional-high-first',wire,false);
            codecControl(wire,'stock-low-first',conventional,true);
            witness={phase:phase,option_type:candidate.type,option_name:candidate.name,padded_bytes:padded,plaintext:plaintext,
                token_ciphertext_hex:conventional,wire_token_hex:wire,witness_path:witnessPath};
            const text='schema_version = 3\nphase = "'+phase+'"\noption_type = '+candidate.type+'\noption_name = "'+candidate.name+'"\npadded_bytes = '+padded+'\nplaintext = "'+plaintext+'"\ntoken_ciphertext_hex = "'+conventional+'"\nwire_token_hex = "'+wire+'"\n';
            writeFile(witnessPath,Array.from(text,c=>c.charCodeAt(0)));
            event('catalog-candidate-witness',witness);
            event('synthetic-crypto-roundtrip',Object.assign({},witness,{token_roundtrip:true,wire_codec_roundtrip:true,synthetic_only:true}));
        }
        store.initialize('reload');
        call('CApiLicense::init', fn('_ZN11CApiLicense4initEv','void',['pointer']),[license]);
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
        const expectedAfter=cfg.seed_catalog.map(x=>Object.assign({},x,{valid:x.option_type===candidate.type&&phase!=='negative'?true:x.valid}));
        const expectedBefore=phase==='reload'?expectedAfter:cfg.seed_catalog;
        const before=queryAll('before');
        if(!catalogEqual(before,expectedBefore))throw new Error('Seed catalog mismatch');
        if(phase!=='reload'&&before.find(x=>x.option_type===candidate.type).valid)throw new Error('Candidate already enabled');
        if(phase!=='reload') {
            withString(cfg.installer_family+'-'+candidate.name+'@'+witness.wire_token_hex,'installer-input',obj=>{
                event('ordinary-installer-enter',{option_type:candidate.type,option_name:candidate.name,family:cfg.installer_family,
                    token_hex:witness.wire_token_hex,wire_token_hex:witness.wire_token_hex,token_ciphertext_hex:witness.token_ciphertext_hex,accepted:false,synthetic_only:true});
                const result=call('ApiLicense_SetLicenseInstall',fn('_ZN11CApiLicense28ApiLicense_SetLicenseInstallE7RString','int',['pointer','pointer']),[license,obj]);
                event('ordinary-installer-return',{result:result,acceptance_claimed:false});
            });
        }
        capabilityChecks=capability.evaluate(utility);
        const after=queryAll('after');
        store.snapshot(checkpoint+'-after');
        const licenseBytes=readFile(candidatePath,true);
        const licenseMatches=licenseBytes!==null&&String.fromCharCode.apply(null,licenseBytes).trim()===candidate.name+'@'+witness.wire_token_hex;
        const preserved=seeded.filter(x=>x.path!=='model/private.mem').every(x=>equal(readFile(guestPath(x.path),false),x.data));
        const candidateVerify=verifyReturns.filter(x=>x.option_type===candidate.type&&x.consumer_call==='ApiLicense_SetLicenseInstall');
        const checks={started_false:!call('API_GetStarted:final',started),catalog_complete:before.length===14&&after.length===14,
            seed_catalog_matches:catalogEqual(before,expectedBefore),seed_inputs_preserved:preserved,private_reloaded:true,catalog_delta_exact:catalogEqual(after,expectedAfter),
            candidate_file_matches:phase==='negative'?licenseBytes===null:licenseMatches};
        if(phase!=='reload'){checks.token_roundtrip=true;checks.wire_codec_roundtrip=true;checks.baseline_candidate_disabled=!before.find(x=>x.option_type===candidate.type).valid;}
        if(phase==='negative') {
            checks.negative_rejected=activeReturns.length===1&&activeReturns[0]===24527&&candidateVerify.length===1&&!candidateVerify[0].valid&&errorCodes.includes(24527)&&!errorCodes.includes(24531);
            checks.negative_no_license_file=licenseBytes===null;
        } else if(phase==='positive') {
            checks.positive_accepted=activeReturns.length===1&&activeReturns[0]===24531&&candidateVerify.length===1&&candidateVerify[0].valid&&errorCodes.includes(24531);
            checks.positive_license_file=licenseMatches;
        } else {
            checks.reload_persisted=catalogEqual(before,expectedAfter)&&catalogEqual(after,expectedAfter)&&licenseMatches;
            checks.no_installer=activeReturns.length===0;checks.no_token_regeneration=true;
        }
        Object.assign(checks,capabilityChecks);
        const details={phase:phase,catalog_experiment:true,candidate_type:candidate.type,candidate_name:candidate.name,expected_checks:checks,
            catalog_before:before,catalog_after:after,active_returns:activeReturns,verify_returns:verifyReturns,stock_codes:errorCodes,
            persistence_backend:'stock-memfile-harness-directed-file',physical_contact:false};
        event('entitlement-phase-evaluation',details);
        if(!Object.keys(checks).every(k=>checks[k]===true)){stop('failure','entitlement-phase-expectation-mismatch',78,details);return;}
        stop('dependency-stop','option-catalog-phase-complete',77,details);
    } catch(error) {
        stop('failure','entitlement-catalog-error',78,Object.assign({phase:entitlementPhase,message:String(error)},faultDetails(error)));
    }
}
