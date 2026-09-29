// Frida 16.7.19, ARM64/API-25 disposable guest. The controller pins all input hashes.
// This observes stock constructors and stops before the first FPGA DNA request.
// No option installation, register response, service-return substitution, or binary edit.
'use strict';

const LIB_DIRECTORY = '/data/local/tmp/entitlement/lib/';
const STOCK_AUKLET_SHA256 = '4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e';
// Keep native exceptions in the caller and preserve their Error.context before termination.
const NATIVE_OPTIONS = { exceptions: 'steal', scheduling: 'cooperative' };
const listeners = [];
let sequence = 0;
let terminating = false;
let currentCall = 'script-start';
let aukletModule = null;
let factoryTraceCount = 0;
const FACTORY_TRACE_LIMIT = 96;
const journal = new File('/data/local/tmp/entitlement/events.jsonl', 'w');

function event(kind, details) {
    const payload = Object.assign({ kind: kind, sequence: ++sequence, call: currentCall }, details || {});
    journal.write(JSON.stringify(payload) + '\n');
    journal.flush();
    send(payload);
}

function location(address) {
    if (address === undefined || address === null) return null;
    const value = ptr(address);
    const result = { address: value.toString() };
    const owner = Process.findModuleByAddress(value);
    if (owner !== null) {
        result.module = owner.name;
        result.module_offset = value.sub(owner.base).toString();
    }
    if (aukletModule !== null && value.compare(aukletModule.base) >= 0 &&
        value.compare(aukletModule.base.add(aukletModule.size)) < 0) {
        result.auklet_offset = value.sub(aukletModule.base).toString();
    }
    return result;
}

function readableMapping(address) {
    const range = Process.findRangeByAddress(address);
    return range === null ? null : { base: range.base.toString(), size: range.size,
        protection: range.protection };
}

function faultDetails(exception) {
    const details = { exception_type: exception.type || null, address: location(exception.address) };
    if (exception.memory !== undefined && exception.memory !== null) {
        details.memory = { operation: exception.memory.operation,
            address: location(exception.memory.address) };
    }
    if (exception.context !== undefined && exception.context !== null) {
        const context = exception.context;
        const registers = {};
        ['pc', 'lr', 'sp', 'fp'].concat(Array.from({ length: 29 }, (_, i) => 'x' + i))
            .forEach(function (name) {
                if (context[name] !== undefined) registers[name] = context[name].toString();
            });
        details.registers = registers;
        details.pc = location(context.pc);
        details.lr = location(context.lr);
    }
    return details;
}

function factoryTrace(kind, details) {
    if (currentCall !== 'CApiFactory::Api_Create') return;
    if (factoryTraceCount < FACTORY_TRACE_LIMIT) {
        ++factoryTraceCount;
        event(kind, details);
    } else if (factoryTraceCount === FACTORY_TRACE_LIMIT) {
        ++factoryTraceCount;
        event('factory-trace-limit', { limit: FACTORY_TRACE_LIMIT });
    }
}

function observeFactory(module) {
    // Slots recovered statically from the pinned Base constructor; read targets, never replace them.
    const slots = [
        ['operator-new', 0xb7c3f0], ['string-copy', 0xb780a8], ['service-item-ctor', 0xb85138],
        ['string-destructor', 0xb86ab0], ['add-item', 0xb865d8], ['operator-delete', 0xb7d9f0],
        ['base-vtable', 0xb8e318], ['service-vector', 0xb8e0b8]
    ];
    slots.forEach(function (entry) {
        const slot = module.base.add(entry[1]);
        const target = slot.readPointer();
        event('factory-got-slot', { name: entry[0], slot: location(slot), target: location(target),
            target_mapping: readableMapping(target) });
    });
    const seen = new Set();
    module.enumerateExports().filter(function (entry) {
        return entry.type === 'function' &&
            (/^_ZN(11CApiUtility|8CApiCore|8CApiBase|12struServItem)C[12]E/.test(entry.name) ||
             /^_ZN8CApiBase7addItemE/.test(entry.name) ||
             /^_ZN11CApiFactory(10Api_Create|12Api_Register)E/.test(entry.name));
    }).forEach(function (entry) {
        const key = entry.address.toString();
        if (seen.has(key)) return;
        seen.add(key);
        listeners.push(Interceptor.attach(entry.address, {
            onEnter: function (args) {
                const details = { function: entry.name, target: location(entry.address),
                    caller: location(this.returnAddress), thread_id: this.threadId };
                if (/^_ZN8CApiBaseC[12]E/.test(entry.name)) {
                    details.base_this = location(args[0]);
                    details.name_object = location(args[1]);
                    details.service_id = args[2].toInt32();
                    details.base_mapping = readableMapping(args[0]);
                    details.name_mapping = readableMapping(args[1]);
                }
                factoryTrace('factory-call-enter', details);
            },
            onLeave: function () {
                // Constructors have no portable return value; record only that control returned.
                factoryTrace('factory-call-return', { function: entry.name, thread_id: this.threadId });
            }
        }));
    });
    event('factory-observers-installed', { unique_addresses: seen.size, event_limit: FACTORY_TRACE_LIMIT });
}

function requiredExport(module, name) {
    const address = Module.findExportByName(module, name);
    if (address === null) throw new Error('Missing export: ' + name);
    return address;
}

const nativeExit = new NativeFunction(requiredExport('libc.so', '_exit'), 'void', ['int'], NATIVE_OPTIONS);
const nativeWrite = new NativeFunction(requiredExport('libc.so', 'write'), 'long',
    ['int', 'pointer', 'ulong'], NATIVE_OPTIONS);

function stop(kind, reason, code, details) {
    if (terminating) return;
    terminating = true;
    const marker = 'ENTITLEMENT_BASELINE_STOP ' + kind + ' ' + reason + ' exit=' + code + '\n';
    const bytes = Memory.allocUtf8String(marker);
    event('call-enter', { function: 'libc.write', purpose: 'terminal-marker' });
    nativeWrite(2, bytes, marker.length);
    // Terminal must be the last journal record. The controller acknowledges a durable host receipt.
    event(kind, Object.assign({ reason: reason, exit_code: code, terminal_ack: true }, details || {}));
    // The controller's bounded timeout terminates the process if acknowledgement never arrives.
    recv('terminal-ack', function () {}).wait();
    nativeExit(code);
}

function invoke(label, fn, args) {
    currentCall = label;
    event('call-enter', { function: label });
    const result = fn.apply(null, args || []);
    event('call-return', { function: label, result: result === undefined ? null : String(result) });
    return result;
}

function native(module, name, result, args) {
    return new NativeFunction(requiredExport(module, name), result, args, NATIVE_OPTIONS);
}

function observeStop(address, reason, kind, code) {
    listeners.push(Interceptor.attach(address, {
        onEnter: function () {
            stop(kind || 'failure', reason, code || 78, { address: address.toString() });
        }
    }));
}

function checkedLocalFunction(module, offset, expectedBytes, result, args) {
    const address = module.base.add(offset);
    const actual = Array.from(new Uint8Array(address.readByteArray(expectedBytes.length / 2)),
        function (byte) { return ('0' + byte.toString(16)).slice(-2); }).join('');
    if (actual !== expectedBytes) throw new Error('Stock helper byte mismatch at ' + offset.toString(16));
    event('stock-helper-verified', { elf_va: '0x' + offset.toString(16), bytes: actual });
    return new NativeFunction(address, result, args, NATIVE_OPTIONS);
}

function loadLibrary(name) {
    currentCall = 'Module.load:' + name;
    event('call-enter', { function: currentCall });
    const module = Module.load(LIB_DIRECTORY + name);
    event('call-return', { function: currentCall, base: module.base.toString(), size: module.size });
    return module;
}

function main() {
    try {
        if (Process.arch !== 'arm64' || Process.pointerSize !== 8) {
            throw new Error('This baseline requires the pinned ARM64 guest');
        }
        event('baseline-start', {
            expected_auklet_sha256: STOCK_AUKLET_SHA256,
            input_hash_validation: 'controller-required',
            pid: Process.id,
            mode: 'stock-native-construction-then-dna-stop'
        });

        Process.setExceptionHandler(function (exception) {
            stop('failure', 'native-exception', 78, faultDetails(exception));
            return false;
        });
        ['abort', '__assert2', '__stack_chk_fail'].forEach(function (name) {
            const address = Module.findExportByName('libc.so', name);
            if (address !== null) observeStop(address, 'native-' + name);
        });

        loadLibrary('libc++_shared.so');
        loadLibrary('libfftw3f.so');
        const auklet = loadLibrary('libscope-auklet.so');
        aukletModule = auklet;
        const moduleName = auklet.name;
        observeFactory(auklet);

        observeStop(requiredExport(moduleName, '_ZN11CApiUtility17ApiUtility_GetDNAEv'),
            'runtime-dna-unavailable', 'dependency-stop', 77);
        observeStop(requiredExport(moduleName, 'Dev_PCIeInit'), 'unexpected-pcie-init', 'dependency-stop', 77);
        observeStop(requiredExport(moduleName, '_ZN9CApiSetup11loadPrivacyEv'),
            'private-fram-unavailable', 'dependency-stop', 77);
        listeners.push(Interceptor.attach(requiredExport(moduleName, '_ZN8CApiCore9syncErrorEi'), {
            onEnter: function (args) {
                stop('failure', 'stock-sync-error', 78, { stock_code: args[0].toInt32() });
            }
        }));

        const create = native(moduleName, '_ZN11CApiFactory10Api_CreateEv', 'int', []);
        const getServices = native(moduleName, '_ZN11CApiFactory14getServiceListEv', 'pointer', []);
        const at = native(moduleName, '_ZNSt6__ndk16vectorIP8CApiBaseNS_9allocatorIS2_EEE2atEm',
            'pointer', ['pointer', 'ulong']);
        const getId = native(moduleName, '_ZNK8CApiBase5getIdEv', 'int', ['pointer']);
        const productSeries = native(moduleName, '_Z20API_GetProductSeriesv', 'int', []);
        const initVendor = native(moduleName, '_ZN11CApiUtility21ApiUtility_InitVendorEv', 'int', []);
        // Native vector::size helper used by stock Api_Create/Api_Register. No JS vector-layout model.
        const vectorSize = checkedLocalFunction(auklet, 0x238f64,
            'ff4300d1080180d2e00700f9e90740f92a0540f9290140f9', 'ulong', ['pointer']);
        // Native libc++ c_str helper used throughout stock code. Cached globals are live RStrings.
        // This avoids guessing an RString layout or incorrectly calling an x8-sret getter from JS.
        const cString = checkedLocalFunction(auklet, 0x235978,
            'ff8300d1fd7b01a9fd430091e00700f9e00740f90a000094', 'pointer', ['pointer']);
        const stringLength = native('libc.so', 'strnlen', 'ulong', ['pointer', 'ulong']);

        Interceptor.flush();
        const createResult = invoke('CApiFactory::Api_Create', create);
        if (createResult !== 0) throw new Error('Api_Create rejected construction: ' + createResult);

        const services = invoke('CApiFactory::getServiceList', getServices);
        if (services.isNull()) throw new Error('Null service list');
        const count = Number(invoke('stock-vector::size', vectorSize, [services]));
        if (!Number.isSafeInteger(count) || count < 2 || count > 256) {
            throw new Error('Unexpected service count: ' + count);
        }
        const ids = [];
        for (let index = 0; index < count; ++index) {
            const slot = invoke('stock-vector::at[' + index + ']', at, [services, index]);
            if (slot.isNull()) throw new Error('Null service slot');
            const service = slot.readPointer();
            if (service.isNull()) throw new Error('Null service object');
            const id = invoke('CApiBase::getId[' + index + ']', getId, [service]);
            ids.push(id);
            event('service', { index: index, service_id: id, base_subobject: service.toString() });
        }
        if (ids.indexOf(11) === -1 || ids.indexOf(36) === -1) throw new Error('Required services absent');
        event('service-inventory-complete', { count: count, service_ids: ids });

        const modelGlobal = requiredExport(moduleName, '_ZN11CApiUtility14strStaticModelE');
        const serialGlobal = requiredExport(moduleName, '_ZN11CApiUtility15strStaticSerialE');
        const modelChars = invoke('stock-c_str:cached-model', cString, [modelGlobal]);
        const serialChars = invoke('stock-c_str:cached-serial', cString, [serialGlobal]);
        if (modelChars.isNull() || serialChars.isNull()) throw new Error('Null cached identity string');
        const modelLength = Number(invoke('strnlen:cached-model', stringLength, [modelChars, 64]));
        const serialLength = Number(invoke('strnlen:cached-serial', stringLength, [serialChars, 256]));
        if (modelLength === 64 || serialLength === 256) throw new Error('Unbounded cached identity string');
        const series = invoke('API_GetProductSeries', productSeries);
        event('cached-identity', {
            model_present: modelLength > 0,
            model: modelLength === 0 ? '' : modelChars.readUtf8String(modelLength),
            serial_present: serialLength > 0,
            serial_length: serialLength,
            serial_disclosed: false,
            product_series: series,
            initialized_identity_claimed: false,
            options: 'unavailable-before-license-initialization'
        });

        event('vendor-initialization-boundary', { expected_stop: 'ApiUtility_GetDNA-entry' });
        invoke('CApiUtility::ApiUtility_InitVendor', initVendor);
        throw new Error('InitVendor returned without expected DNA boundary');
    } catch (error) {
        stop('failure', 'script-or-native-call-error', 78,
            Object.assign({ message: String(error) }, faultDetails(error)));
    }
}

setImmediate(main);
