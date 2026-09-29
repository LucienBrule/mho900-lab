// Disposable synthetic entitlement fixture only. Stock MemFile serialization,
// with explicit harness-directed file persistence; no claim of FRAM scheduling.
'use strict';

globalThis.entitlementPrivateStore = {
    create: function (module, emit, invokeStock) {
        const directory = '/data/local/tmp/entitlement/model';
        const canonical = directory + '/private.mem';
        const maximum = 0x700; // Stock saveSession requires private size < 0x700.
        const options = { exceptions: 'steal', scheduling: 'cooperative' };
        function exported(owner, name, result, args) {
            const address = Module.findExportByName(owner, name);
            if (address === null) throw new Error('Missing private-store export: ' + name);
            return new NativeFunction(address, result, args, options);
        }
        const object = Module.findExportByName(module.name, '_ZN9CApiSetup12mPrivateDataE');
        if (object === null || !object.equals(module.base.add(0x151b3f0))) {
            throw new Error('Unexpected stock private-store global');
        }
        function stock(name, offset, result, args) {
            const address = Module.findExportByName(module.name, name);
            if (address === null || !address.equals(module.base.add(offset))) {
                throw new Error('Unexpected stock private-store function: ' + name);
            }
            return new NativeFunction(address, result, args, options);
        }
        const format = stock('_ZN9CApiSetup18formatPrivateSetupEv', 0x3f147c, 'int', []);
        const getSize = stock('_ZN7MemFile7getSizeEv', 0x3f2fb0, 'int', ['pointer']);
        const serialOut = stock('_ZN7MemFile9serialOutEPvi', 0x3f2ccc, 'int',
            ['pointer', 'pointer', 'int']);
        const serialIn = stock('_ZN7MemFile8serialInEPv', 0x3f2924, 'int', ['pointer', 'pointer']);
        const modified = stock('_ZN7MemFile10isModifiedEv', 0x3f307c, 'bool', ['pointer']);
        const open = exported('libc.so', 'open', 'int', ['pointer', 'int', 'int']);
        const read = exported('libc.so', 'read', 'long', ['int', 'pointer', 'ulong']);
        const write = exported('libc.so', 'write', 'long', ['int', 'pointer', 'ulong']);
        const fsync = exported('libc.so', 'fsync', 'int', ['int']);
        const close = exported('libc.so', 'close', 'int', ['int']);
        const rename = exported('libc.so', 'rename', 'int', ['pointer', 'pointer']);
        const errnoLocation = exported('libc.so', '__errno', 'pointer', []);
        let initialized = false;

        function nativeCall(label, fn, args) {
            return invokeStock('private-store:' + label, fn, args);
        }
        function error(operation) {
            return new Error('Private-store ' + operation + ' failed, errno=' + errnoLocation().readS32());
        }
        function closeChecked(fd) {
            if (close(fd) !== 0) throw error('close');
        }
        function readFile(path, optional) {
            const fd = open(Memory.allocUtf8String(path), 0x80000, 0);
            if (fd < 0) {
                const number = errnoLocation().readS32();
                if (optional && number === 2) return null;
                throw new Error('Private-store open read failed, errno=' + number);
            }
            const buffer = Memory.alloc(maximum);
            let total = 0;
            try {
                while (total < maximum) {
                    const count = Number(read(fd, buffer.add(total), maximum - total));
                    if (count < 0) throw error('read');
                    if (count === 0) break;
                    total += count;
                }
                if (total >= maximum) throw new Error('Private-store file exceeds stock private-region limit');
                return buffer.readByteArray(total);
            } finally {
                closeChecked(fd);
            }
        }
        function writeExclusive(path, bytes) {
            const data = new Uint8Array(bytes);
            const buffer = Memory.alloc(data.length);
            buffer.writeByteArray(bytes);
            const fd = open(Memory.allocUtf8String(path), 1 | 64 | 128 | 0x80000, 0x180);
            if (fd < 0) throw error('exclusive open');
            try {
                // A short write is evidence of failure, not silently promoted to durable success.
                const count = Number(write(fd, buffer, data.length));
                if (count !== data.length) throw new Error('Private-store short write: ' + count);
                if (fsync(fd) !== 0) throw error('file fsync');
            } finally {
                closeChecked(fd);
            }
        }
        function syncDirectory() {
            // Android ARM64 UAPI: O_DIRECTORY=040000, O_CLOEXEC=02000000 (octal).
            const fd = open(Memory.allocUtf8String(directory), 0x4000 | 0x80000, 0);
            if (fd < 0) throw error('directory open');
            try {
                if (fsync(fd) !== 0) throw error('directory fsync');
            } finally {
                closeChecked(fd);
            }
        }
        function equal(left, right) {
            const a = new Uint8Array(left), b = new Uint8Array(right);
            return a.length === b.length && a.every(function (value, index) { return value === b[index]; });
        }
        function inspect(bytes) {
            const size = bytes.byteLength;
            if (size < 8 || size >= maximum) throw new Error('Invalid private-store stream length');
            const view = new DataView(bytes);
            const total = view.getInt32(0, true);
            if (total !== size || ((view.getUint32(0, true) + view.getUint32(4, true)) >>> 0) !== 0) {
                throw new Error('Invalid private-store stream header');
            }
            const records = [];
            const ids = new Set();
            let cursor = 8;
            while (cursor < total) {
                if (cursor + 20 > total) throw new Error('Truncated private-store record header');
                const id = view.getInt32(cursor, true);
                const length = view.getInt32(cursor + 8, true);
                if (((view.getUint32(cursor, true) + view.getUint32(cursor + 4, true)) >>> 0) !== 0 ||
                    ((view.getUint32(cursor + 8, true) + view.getUint32(cursor + 12, true)) >>> 0) !== 0 ||
                    length <= 0 || cursor + 20 + length > total || ids.has(id)) {
                    throw new Error('Invalid private-store record bounds or duplicate ID');
                }
                ids.add(id);
                records.push({ id: id, length: length });
                cursor += 20 + length;
            }
            if (cursor !== total) throw new Error('Private-store record cursor mismatch');
            return { size: total, record_count: records.length, records: records };
        }
        function serialize() {
            const size = nativeCall('MemFile.getSize', getSize, [object]);
            if (size < 8 || size >= maximum) throw new Error('Stock private-store size outside bounded contract');
            const buffer = Memory.alloc(size);
            const written = nativeCall('MemFile.serialOut', serialOut, [object, buffer, size]);
            if (written !== size) throw new Error('Stock private-store serialization was partial');
            const bytes = buffer.readByteArray(size);
            inspect(bytes);
            return bytes;
        }
        function summary(bytes) {
            const result = inspect(bytes);
            result.modified = nativeCall('MemFile.isModified', modified, [object]);
            result.persistence = 'harness-directed-stock-MemFile';
            return result;
        }
        return {
            preflight: function () {
                syncDirectory();
                emit('private-store-directory-preflight', { directory_open: true,
                    directory_fsync: true, directory_close: true, flags: 0x4000 | 0x80000 });
            },
            initialize: function (mode) {
                if (initialized) throw new Error('Private-store already initialized by this harness');
                if (mode === 'fresh') {
                    if (readFile(canonical, true) !== null) throw new Error('Fresh private-store requires absent canonical file');
                    if (nativeCall('CApiSetup.formatPrivateSetup', format, []) !== 0) {
                        throw new Error('Stock private-store format failed');
                    }
                    const bytes = serialize();
                    const result = summary(bytes);
                    if (result.size !== 8 || result.record_count !== 0) throw new Error('Stock formatted store was not empty');
                    initialized = true;
                    emit('private-store-initialized', Object.assign({ mode: mode }, result));
                    return result;
                }
                if (mode !== 'reload') throw new Error('Unknown private-store initialization mode');
                const bytes = readFile(canonical, false);
                inspect(bytes);
                const buffer = Memory.alloc(bytes.byteLength);
                buffer.writeByteArray(bytes);
                const consumed = nativeCall('MemFile.serialIn', serialIn, [object, buffer]);
                if (consumed !== bytes.byteLength) throw new Error('Stock private-store decode count mismatch');
                if (!equal(bytes, serialize())) throw new Error('Stock private-store roundtrip mismatch');
                initialized = true;
                const result = summary(bytes);
                emit('private-store-initialized', Object.assign({ mode: mode, roundtrip_exact: true,
                    stock_crc_validation: true, path: canonical }, result));
                return result;
            },
            snapshot: function (label) {
                if (!initialized) throw new Error('Private-store must be initialized before snapshot');
                if (!/^[a-z0-9][a-z0-9-]{0,47}$/.test(label)) throw new Error('Invalid private-store phase label');
                const bytes = serialize();
                const phase = directory + '/private-' + label + '.mem';
                const pending = directory + '/private-pending-' + label + '.mem';
                writeExclusive(phase, bytes);
                writeExclusive(pending, bytes);
                if (rename(Memory.allocUtf8String(pending), Memory.allocUtf8String(canonical)) !== 0) {
                    throw error('canonical rename');
                }
                syncDirectory();
                if (!equal(bytes, readFile(phase, false)) || !equal(bytes, readFile(canonical, false))) {
                    throw new Error('Private-store durable readback mismatch');
                }
                const result = Object.assign({ label: label, path: phase, canonical_path: canonical,
                    fsync_completed: true, readback_exact: true }, summary(bytes));
                emit('private-store-snapshot', result);
                return result;
            },
            inventory: function () {
                if (!initialized) throw new Error('Private-store must be initialized before inventory');
                return summary(serialize());
            }
        };
    }
};
