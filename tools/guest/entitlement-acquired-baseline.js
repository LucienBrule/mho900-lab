// Acquired identity inputs in a disposable ART component. Private storage is modeled.
// Factory/identity setup follows entitlement-synthetic.js; no installer or producer is called.
'use strict';
const entitlementAcquiredKeepalive = [];
function entitlementExperiment() {
    try {
        const cfg = acquiredKeyFixture;
        const phase = 'acquired-baseline';
        if (cfg.schema_version !== 1 || cfg.physical_contact !== false ||
            cfg.private_store !== 'fresh-modeled' || cfg.key_field_hex.length !== 260 ||
            cfg.key_ciphertext_hex.length !== 296 || cfg.file_keys_hex.length !== 32)
            throw new Error('Unexpected acquired baseline fixture');
        const mod = aukletModule;
        if (mod === null || Process.arch !== 'arm64') throw new Error('ART/Auklet not ready');
        const nm = mod.name;
        event('entitlement-phase-start', { phase: phase, identity: 'acquired-cached-fixture', model: cfg.model,
            serial: cfg.serial, dna_hex: cfg.dna_hex, stock_files_unchanged: true,
            stock_apk_unchanged: true, native_library_derived: false });
        function fn(name, result, args) { return native(nm, name, result, args); }
        function guarded(va, bytes, result, args) {
            return checkedLocalFunction(mod, va, bytes, result, args);
        }
        function call(label, f, args) { return invoke(label, f, args); }
        function bytes(p, n) { return Array.from(new Uint8Array(p.readByteArray(n))); }
        function hex(arr) { return arr.map(x => ('0' + x.toString(16)).slice(-2)).join(''); }
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
        const activeReturns = [], verifyReturns = [], errorCodes = [];
        const activeAddress = requiredExport(nm, '_ZN11CApiLicense9activeOptE7OptTypeR7RString');
        const verifyAddress = requiredExport(nm, '_ZN11CApiLicense12verifyOptionEP8COptInfoR7RStringS3_');
        listeners.push(Interceptor.attach(activeAddress, {
            onEnter(args) { this.optionType = args[1].toInt32(); event('stock-active-enter', { option_type: this.optionType }); },
            onLeave(ret) { activeReturns.push(ret.toInt32()); event('stock-active-return', { option_type: this.optionType, result: ret.toInt32() }); }
        }));
        listeners.push(Interceptor.attach(verifyAddress, {
            onEnter() { event('stock-verify-enter', {}); },
            onLeave(ret) { const valid = (ret.toInt32() & 1) !== 0; verifyReturns.push(valid); event('stock-verify-return', { valid: valid }); }
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
        entitlementAcquiredKeepalive.push(dnaResponse);
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
            file_keys_hex: hex(bytes(fileKeys, 16)), acquired_material: true });
        const keyPath = '/rigol/data/Key.data';
        const initialKey = readFile(keyPath, false);
        if (hex(initialKey) !== cfg.key_ciphertext_hex) throw new Error('Acquired ciphertext mismatch');
        if (hex(bytes(fileKeys, 16)) !== cfg.file_keys_hex) throw new Error('Acquired cached keys mismatch');
        const countString = guarded(0x23df40, 'ffc300d1fd7b02a9fd830091a0831ff8', 'ulong', ['pointer']);
        const keyOutputs = [];
        listeners.push(Interceptor.attach(requiredExport(nm, '_ZN11CApiLicense13getLicenseKeyER7RStringS1_'), {
            onEnter(args) { this.key = args[1]; this.identity = args[2]; },
            onLeave() {
                const n = Number(countString(this.key));
                if (n > 512) throw new Error('Unexpected key field length');
                const output = { key_length: n, key_hex: hex(bytes(cstr(this.key), n)),
                    identity: cstr(this.identity).readUtf8String() };
                keyOutputs.push(output);
                event('acquired-key-outputs', output);
            }
        }));
        store.initialize('fresh');
        store.snapshot('acquired-before');
        call('CApiLicense::init', fn('_ZN11CApiLicense4initEv', 'void', ['pointer']), [license]);
        const snapshot = store.snapshot('acquired-after');
        const catalog = [[0,'BND'],[1,'EMBD'],[2,'COMP'],[3,'AUTO'],[4,'AUTOA'],[5,'FlexA'],[6,'AUDIOA'],[7,'AEROA'],[19,'RLU05'],[30,'AFG50'],[29,'AFG100'],[22,'BWU03T05'],[23,'BWU03T08'],[24,'BWU05T08']];
        const query = fn('_ZN11CApiLicense26ApiLicense_GetLicenseValidE7OptTypeRb', 'int', ['pointer', 'int', 'pointer']);
        const out = Memory.alloc(1);
        const options = catalog.map(item => {
            out.writeU8(0);
            const status = call('GetLicenseValid:' + item[1], query, [license, item[0], out]);
            if (status !== 0) throw new Error('Catalog query failed');
            return { option_type: item[0], option_name: item[1], valid: out.readU8() !== 0, status: status };
        });
        event('option-catalog', { options: options, private_state: 'fresh-modeled', specimen_options_unknown: true });
        const checks = {
            key_outputs_exact: keyOutputs.length === 1 && keyOutputs[0].key_length === 130 && keyOutputs[0].key_hex === cfg.key_field_hex && keyOutputs[0].identity === cfg.serial,
            file_keys_exact: hex(bytes(fileKeys, 16)) === cfg.file_keys_hex,
            key_file_unchanged: hex(readFile(keyPath, false)) === cfg.key_ciphertext_hex,
            fresh_private_store: true,
            catalog_complete: options.length === 14,
            no_installer: activeReturns.length === 0,
            started_false: !call('API_GetStarted:final', started)
        };
        if (!Object.values(checks).every(x => x === true)) throw new Error('Acquired baseline checks failed');
        stop('dependency-stop', 'acquired-key-baseline-complete', 77, { expected_checks: checks,
            catalog: options, private_snapshot: snapshot, physical_contact: false, specimen_options_unknown: true });
    } catch (error) {
        stop('failure', 'acquired-key-baseline-error', 78, Object.assign({ message: String(error) }, faultDetails(error)));
    }
}
