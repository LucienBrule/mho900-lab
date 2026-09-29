// Composed with the pinned ART and baseline helpers. All personality inputs are synthetic.
// Only the FPGA DNA data response is modeled; stock license parsing/validation stays intact.
'use strict';
const entitlementSyntheticKeepalive = [];

function entitlementExperiment() {
    try {
        const cfg = entitlementFixture;
        const phase = entitlementPhase;
        const checkpoint = entitlementCheckpoint;
        if (!['negative', 'install', 'process-reload', 'reboot-reload'].includes(checkpoint)) throw new Error('Unknown checkpoint');
        if (!['negative', 'positive', 'reload'].includes(phase)) throw new Error('Unknown phase');
        if (cfg.stock_native_sha256 !== STOCK_AUKLET_SHA256 || cfg.token_text_encoding !== 'low-nibble-first' ||
            cfg.consumer_observation_required !== true || cfg.option_type !== 5 ||
            cfg.option_name !== 'FlexA' || cfg.license_type !== 0 || cfg.license_time !== 0 ||
            cfg.aes_key_ascii.length !== 32 || cfg.key_file_plaintext.length !== 40 ||
            cfg.key_file_plaintext !== cfg.serial + ';' + cfg.aes_key_ascii ||
            cfg.token_padded_bytes !== 32 || cfg.physical_contact !== false ||
            cfg.specimen_key_files_used !== false) throw new Error('Unexpected frozen synthetic fixture');
        const mod = aukletModule;
        if (mod === null || Process.arch !== 'arm64') throw new Error('ART/Auklet not ready');
        const nm = mod.name;
        // Check original bytes before the consumer observer patches this entry for observation.
        const stockDecode = guarded(0x242fe8, 'ff0301d1fd7b03a9fdc30091a1831ff8', 'void', ['pointer', 'pointer', 'pointer']);
        if (typeof entitlementObserveConsumer !== 'function') throw new Error('Required consumer observer missing');
        entitlementObserveConsumer(mod, event, cfg);
        event('entitlement-phase-start', { phase: phase, identity: 'synthetic', model: cfg.model,
            serial: cfg.serial, dna_hex: cfg.dna_hex, stock_files_unchanged: true });
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
            const opened = call('open-write:' + path, open, [Memory.allocUtf8String(path), 0x241, 0x180]);
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
        entitlementSyntheticKeepalive.push(dnaResponse);
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
        if (rawBandwidth !== 17 || systemBandwidth !== 17) throw new Error('Unexpected stock MHO984 bandwidth');
        call('ApiUtility_GetDNA', guarded(0x42a7dc, 'ff0302d1fd7b07a9fdc3019148d03bd5', 'void', []));
        const actualDna = requiredExport(nm, '_ZN11CApiUtility5m_DNAE').readU64();
        if (actualDna.compare(uint64('0x' + cfg.dna_hex)) !== 0) throw new Error('Stock DNA side effect differs');
        const fileKeys = requiredExport(nm, 'fileKeys');
        call('ApiUtility_ConvertDNA2Key', guarded(0x42a91c, 'ff8300d1fd7b01a9fd430091083b00f0', 'void', ['pointer']), [fileKeys]);
        event('synthetic-identity-confirmed', { model: observedModel, serial: observedSerial, dna_hex: cfg.dna_hex,
            file_keys_hex: hex(bytes(fileKeys, 16)), acquired_material: false });
        const keyPath = '/rigol/data/Key.data', licensePath = '/rigol/data/FlexA.lic';
        const witnessPath = '/data/local/tmp/entitlement/model/crypto-witness.toml';
        const existingKey = readFile(keyPath, true);
        let token = null;
        let tokenCiphertextHex = null;
        if (phase === 'reload') {
            const witnessBytes = readFile(witnessPath, false);
            const witness = String.fromCharCode.apply(null, witnessBytes);
            const match = /^schema_version = 2\nphase = "positive"\nkey_ciphertext_hex = "([0-9a-f]{80})"\ntoken_ciphertext_hex = "([0-9a-f]{64})"\nwire_token_hex = "([0-9a-f]{64})"\n$/.exec(witness);
            if (match === null || existingKey === null || hex(existingKey) !== match[1]) throw new Error('Reload saved witness/key mismatch');
            tokenCiphertextHex = match[2];
            token = match[3];
            if (token !== tokenCiphertextHex.replace(/../g, pair => pair[1] + pair[0])) throw new Error('Saved wire encoding differs');
            const savedLicense = readFile(licensePath, false);
            if (String.fromCharCode.apply(null, savedLicense).trim() !== cfg.option_name + '@' + token) throw new Error('Reload saved witness/license mismatch');
            event('synthetic-persisted-inputs-read', { witness_path: witnessPath, key_ciphertext_hex: match[1], token_ciphertext_hex: tokenCiphertextHex, wire_token_hex: token, crypto_regenerated: false, inputs_overwritten: false });
        } else {
            const teaSet = guarded(0x3be7e4, 'ff8300d1080080d2c93f00b029610891', 'void', ['pointer']);
            const teaEncode = guarded(0x3be880, 'ff8300d1fd7b01a9fd430091880080d2', 'int', ['pointer', 'long']);
            const teaDecode = fn('_ZN6CXXTEA6decodeEPil', 'int', ['pointer', 'long']);
            const keyPlain = ascii(cfg.key_file_plaintext), keyBuffer = Memory.alloc(40);
            keyBuffer.writeByteArray(keyPlain);
            call('CXXTEA::setKeys', teaSet, [fileKeys]);
            if (call('CXXTEA::encode', teaEncode, [keyBuffer, 40]) !== 0) throw new Error('XXTEA encode failed');
            const encryptedKey = bytes(keyBuffer, 40);
            if (call('CXXTEA::decode', teaDecode, [keyBuffer, 40]) !== 0 || !equal(bytes(keyBuffer, 40), keyPlain)) throw new Error('XXTEA roundtrip failed');
            if (existingKey !== null || readFile(licensePath, true) !== null || readFile(witnessPath, true) !== null) throw new Error('Fresh phase is not empty');
            writeFile(keyPath, encryptedKey);
            const encSchedule = Memory.alloc(256), decSchedule = Memory.alloc(256);
            const aesKey = Memory.allocUtf8String(cfg.aes_key_ascii);
            const aesSet = guarded(0x3e9d24, 'ff4301d1fd7b04a9fd03019148d03bd5', 'int', ['pointer', 'int', 'pointer']);
            const aesEncrypt = guarded(0x3ea76c, 'ff4303d1fc6f07a9fa6708a9f85f09a9', 'void', ['pointer', 'pointer', 'pointer']);
            const aesDecSet = fn('AES_set_decrypt_key', 'int', ['pointer', 'int', 'pointer']);
            const aesDecrypt = fn('AES_decrypt', 'void', ['pointer', 'pointer', 'pointer']);
            if (call('AES_set_encrypt_key', aesSet, [aesKey, 256, encSchedule]) !== 0 ||
                call('AES_set_decrypt_key', aesDecSet, [aesKey, 256, decSchedule]) !== 0) throw new Error('AES schedule failed');
            function makeToken(text) {
                const plain = ascii(text);
                if (plain.length >= 32) throw new Error('Token plaintext too long');
                while (plain.length < 32) plain.push(0);
                const src = Memory.alloc(32), dst = Memory.alloc(32), recovered = Memory.alloc(32);
                src.writeByteArray(plain);
                for (let i = 0; i < 32; i += 16) {
                    call('AES_encrypt:block' + i, aesEncrypt, [src.add(i), dst.add(i), encSchedule]);
                    call('AES_decrypt:roundtrip' + i, aesDecrypt, [dst.add(i), recovered.add(i), decSchedule]);
                }
                if (!equal(bytes(recovered, 32), plain)) throw new Error('AES roundtrip failed');
                return hex(bytes(dst, 32));
            }
            tokenCiphertextHex = makeToken(phase === 'negative' ? cfg.negative_plaintext : cfg.positive_plaintext);
            token = tokenCiphertextHex.replace(/../g, pair => pair[1] + pair[0]);
            function codecControl(text, encoding, predicted, shouldMatchCiphertext) {
                const destination = Memory.alloc(32), lengthOut = Memory.alloc(4);
                lengthOut.writeS32(-1);
                withString(text, 'codec-' + encoding, obj => {
                    call('API_SetStr2Hex:control:' + encoding, stockDecode, [obj, destination, lengthOut]);
                });
                const length = lengthOut.readS32();
                if (length !== 32) throw new Error('Stock decoder control length differs');
                const decoded = hex(bytes(destination, length));
                const matchesExpected = decoded === tokenCiphertextHex;
                const matchesPrediction = decoded === predicted;
                event('synthetic-wire-codec-control', { input_encoding: encoding, input_text: text,
                    decoded_hex: decoded, decoded_length: length, expected_hex: tokenCiphertextHex,
                    predicted_decoded_hex: predicted, matches_prediction: matchesPrediction,
                    matches_expected: matchesExpected });
                if (!matchesPrediction || matchesExpected !== shouldMatchCiphertext) throw new Error('Stock wire codec control failed');
            }
            codecControl(tokenCiphertextHex, 'conventional-high-first', token, false);
            codecControl(token, 'stock-low-first', tokenCiphertextHex, true);
            const keyHex = hex(encryptedKey);
            const witness = 'schema_version = 2\nphase = "' + phase + '"\nkey_ciphertext_hex = "' + keyHex + '"\ntoken_ciphertext_hex = "' + tokenCiphertextHex + '"\nwire_token_hex = "' + token + '"\n';
            writeFile(witnessPath, Array.from(witness, c => c.charCodeAt(0)));
            event('synthetic-crypto-roundtrip', { phase: phase, key_roundtrip: true, token_roundtrip: true, key_ciphertext_hex: keyHex, token_ciphertext_hex: tokenCiphertextHex, wire_token_hex: token, wire_codec_roundtrip: true, witness_path: witnessPath, synthetic_only: true });
        }
        store.initialize(phase === 'reload' ? 'reload' : 'fresh');
        call('CApiLicense::init', fn('_ZN11CApiLicense4initEv', 'void', ['pointer']), [license]);
        store.snapshot(checkpoint + '-before');
        const catalog = [[0,'BND'],[1,'EMBD'],[2,'COMP'],[3,'AUTO'],[4,'AUTOA'],[5,'FlexA'],[6,'AUDIOA'],[7,'AEROA'],[19,'RLU05'],[30,'AFG50'],[29,'AFG100'],[22,'BWU03T05'],[23,'BWU03T08'],[24,'BWU05T08']];
        const query = fn('_ZN11CApiLicense26ApiLicense_GetLicenseValidE7OptTypeRb', 'int', ['pointer', 'int', 'pointer']);
        function queryAll(label) {
            const out = Memory.alloc(1);
            const result = catalog.map(item => {
                out.writeU8(0);
                const status = call('GetLicenseValid:' + label + ':' + item[1], query, [license, item[0], out]);
                if (status !== 0) throw new Error('Catalog query failed: ' + item[1]);
                return { option_type: item[0], option_name: item[1], valid: out.readU8() !== 0, status: status };
            });
            event('option-catalog', { phase: phase, checkpoint: label, options: result });
            return result;
        }
        const before = queryAll('before');
        const candidate = list => list.find(x => x.option_type === 5).valid;
        if (phase !== 'reload' && before.some(x => x.valid && ![1, 2, 3].includes(x.option_type))) {
            throw new Error('Fresh fixture has a nonbuiltin enabled option');
        }
        if (phase !== 'reload') {
            withString(cfg.installer_family + '-' + cfg.option_name + '@' + token, 'installer-input', obj => {
                event('ordinary-installer-enter', { option_type: cfg.option_type, option_name: cfg.option_name, family: cfg.installer_family, token_hex: token, wire_token_hex: token, token_ciphertext_hex: tokenCiphertextHex, accepted: false, synthetic_only: true });
                const result = call('ApiLicense_SetLicenseInstall', fn('_ZN11CApiLicense28ApiLicense_SetLicenseInstallE7RString', 'int', ['pointer', 'pointer']), [license, obj]);
                event('ordinary-installer-return', { result: result, acceptance_claimed: false });
            });
        }
        const after = queryAll('after');
        store.snapshot(checkpoint + '-after');
        const licenseBytes = readFile(licensePath, true);
        const expectedFile = cfg.option_name + '@' + token;
        const actualFile = licenseBytes === null ? null : String.fromCharCode.apply(null, licenseBytes).trim();
        const checks = { started_false: !call('API_GetStarted:final', started), catalog_complete: before.length === 14 && after.length === 14 };
        if (phase !== 'reload') { checks.key_roundtrip = true; checks.token_roundtrip = true; checks.wire_codec_roundtrip = true; }
        if (phase === 'negative') {
            checks.baseline_candidate_disabled = !candidate(before);
            checks.negative_rejected = !candidate(after) && activeReturns.length === 1 && activeReturns[0] >= 24518 && activeReturns[0] <= 24528 && verifyReturns.includes(false) && errorCodes.includes(activeReturns[0]) && !errorCodes.includes(24531);
            checks.negative_no_license_file = licenseBytes === null;
        } else if (phase === 'positive') {
            checks.baseline_candidate_disabled = !candidate(before);
            checks.positive_accepted = candidate(after) && activeReturns.length === 1 && activeReturns[0] === 24531 && verifyReturns.includes(true) && errorCodes.includes(24531);
            checks.positive_license_file = actualFile === expectedFile;
        } else {
            checks.key_matches_saved_witness = true;
            checks.license_matches_saved_witness = actualFile === expectedFile;
            checks.reload_persisted = candidate(before) && candidate(after) && activeReturns.length === 0 && verifyReturns.includes(true);
            checks.positive_license_file = actualFile === expectedFile;
        }
        const details = { phase: phase, expected_checks: checks, catalog_before: before, catalog_after: after,
            active_returns: activeReturns, verify_returns: verifyReturns, stock_codes: errorCodes,
            persistence_backend: 'stock-memfile-harness-directed-file', physical_contact: false };
        event('entitlement-phase-evaluation', details);
        if (!Object.keys(checks).every(k => checks[k] === true)) {
            stop('failure', 'entitlement-phase-expectation-mismatch', 78, details);
            return;
        }
        stop('dependency-stop', 'entitlement-phase-complete', 77, details);
    } catch (error) {
        stop('failure', 'entitlement-synthetic-error', 78,
            Object.assign({ phase: entitlementPhase, message: String(error) }, faultDetails(error)));
    }
}
