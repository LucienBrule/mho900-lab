// Frida injected bridge. Only libc arguments and private control pages are changed.
'use strict';
const libc = name => Module.getExportByName('libc.so', name);
// Keep a logical event's sequence assignment and POSIX write in one JS critical section.
const call = (name, result, args) => new NativeFunction(libc(name), result, args, {scheduling: 'exclusive'});
const open = call('open', 'int', ['pointer', 'int', 'int']);
const read = call('read', 'long', ['int', 'pointer', 'ulong']);
const write = call('write', 'long', ['int', 'pointer', 'ulong']);
const close = call('close', 'int', ['int']);
if (call('getuid', 'uint', [])() !== 1000) throw new Error('Wrong UID');
const commandFd = open(Memory.allocUtf8String('/proc/self/cmdline'), 0, 0);
const command = Memory.alloc(256);
if (commandFd < 0 || read(commandFd, command, 255) <= 0) throw new Error('No command line');
close(commandFd);
if (command.readUtf8String() !== 'com.rigol.scope') throw new Error('Wrong process');
const stock = Process.getModuleByName('libscope-auklet.so');
// External harness verifies complete installed APK and packaged ELF hashes before injection.
for (const [offset, word] of [[0x27043c, 0xb9000109], [0x270604, 0xb9400109], [0x27056c, 0xf9000128]]) {
    if (stock.base.add(offset).readU32() !== word) throw new Error('Stock instruction mismatch');
}
const evidenceFd = open(Memory.allocUtf8String('/data/data/com.rigol.scope/files/mapping-events.toml'), 0x241, 0x180);
if (evidenceFd < 0) throw new Error('Cannot open evidence');
function persist(line) {
    const bytes = Memory.allocUtf8String(line);
    if (Number(write(evidenceFd, bytes, line.length)) !== line.length) throw new Error('Short evidence write');
}
persist('schema_version = "mho900-lab.mapping-events/1"\n');
let sequence = 0;
function event(kind, fields) {
    let line = '\n[[events]]\nsequence = ' + (++sequence) + '\nkind = ' + JSON.stringify(kind) + '\n';
    for (const key of Object.keys(fields)) line += key + ' = ' + JSON.stringify(fields[key]) + '\n';
    persist(line);
    console.log('MAPPING ' + kind + ' ' + JSON.stringify(fields));
}
function relative(address) { return address.sub(stock.base).toString(); }
let region = null;
const size = 0x1000000;
let descriptor = -1;
let armed = false;
let expectedControl = null;
let controlCount = 0;
const control = Memory.alloc(Process.pageSize);
if (!Memory.protect(control, Process.pageSize, '---')) throw new Error('Control protection failed');
Process.setExceptionHandler(details => {
    if (details.type !== 'access-violation' || details.memory === undefined) return false;
    if (expectedControl !== null && details.memory.address.equals(control.add(16))) {
        if (!details.context.pc.equals(expectedControl.pc) || details.memory.operation !== expectedControl.operation) {
            event('control-failed', {operation: details.memory.operation});
            return false;
        }
        event('control-fault', {operation: expectedControl.operation, width: expectedControl.width,
            source: details.context.x1.toString()});
        controlCount++;
        // Only a private, known test instruction is skipped; no stock instruction is skipped.
        details.context.pc = details.context.pc.add(4);
        return true;
    }
    if (region !== null && details.memory.address.compare(region) >= 0 &&
        details.memory.address.compare(region.add(size)) < 0) {
        const pc = details.context.pc;
        const word = pc.readU32();
        const simpleInteger = (word & 0x3f000000) === 0x39000000;
        const width = simpleInteger ? (1 << (word >>> 30)) : 0;
        const register = word & 31;
        const value = register === 31 ? ptr(0) : details.context['x' + register];
        let trace = 'unavailable';
        try {
            trace = Thread.backtrace(details.context, Backtracer.ACCURATE).map(address => {
                const module = Process.findModuleByAddress(address);
                return module === null ? 'unresolved' : module.name + '+' + address.sub(module.base);
            }).join(',');
        } catch (_) { /* Keep the primary access even if stack unwinding is unavailable. */ }
        event('unsupported-mmio', {operation: details.memory.operation,
            offset: details.memory.address.sub(region).toString(), width: width,
            pc: relative(pc), instruction: Instruction.parse(pc).toString(),
            opcode: '0x' + word.toString(16), register: register,
            value_before: value === undefined ? 'unknown' : value.toString(),
            thread: Process.getCurrentThreadId(), backtrace: trace, completed: false});
        // Fail closed. Deliver the real protection fault; do not invent a register value.
        return false;
    }
    event('unhandled-fault', {type: details.type, operation: details.memory.operation,
        address: details.memory.address.toString(), region: region === null ? 'none' : region.toString()});
    return false;
});
const code = Memory.alloc(Process.pageSize);
// Each private control is one ARM64 load/store followed by RET.
const instructions = [0xb9000001, 0xb9400002, 0xf9000001, 0xf9400002];
Memory.patchCode(code, 32, writable => {
    instructions.forEach((instruction, index) => {
        writable.add(index * 8).writeU32(instruction);
        writable.add(index * 8 + 4).writeU32(0xd65f03c0);
    });
});
if (!Memory.protect(code, Process.pageSize, 'r-x')) throw new Error('Control code protection failed');
for (let index = 0; index < 4; index++) {
    expectedControl = {pc: code.add(index * 8), operation: index % 2 === 0 ? 'write' : 'read',
        width: index < 2 ? 4 : 8};
    const invoke = new NativeFunction(expectedControl.pc, 'void', ['pointer', 'uint64'], {exceptions: 'propagate'});
    invoke(control.add(16), uint64('0x1122334455667788'));
}
expectedControl = null;
if (controlCount !== 4) throw new Error('Missing control faults');
const ordinary = Memory.alloc(8);
ordinary.writeU64(uint64('0x0123456789abcdef'));
if (ordinary.readU64().toString(16) !== '123456789abcdef') throw new Error('Ordinary memory changed');
event('controls-passed', {faults: controlCount, ordinary_memory: true});
const nullPath = Memory.allocUtf8String('/dev/null');
Interceptor.attach(libc('__open_2'), {
    onEnter(args) {
        this.selected = false;
        if (!armed) return;
        if (args[0].readUtf8String() !== '/dev/xdma0_bypass') return;
        if (!this.returnAddress.equals(stock.base.add(0x270200)) || args[1].toUInt32() !== 0x101002 ||
            descriptor !== -1) {
            event('unsupported-open', {caller: relative(this.returnAddress), flags: args[1].toString()});
            return;
        }
        event('open-request', {path: '/dev/xdma0_bypass', flags: '0x101002', caller: '0x270200'});
        args[0] = nullPath;
        this.selected = true;
    },
    onLeave(result) {
        if (!this.selected) return;
        descriptor = result.toInt32();
        event('open-result', {fd: descriptor, backing: '/dev/null'});
    }
});
Interceptor.attach(libc('mmap'), {
    onEnter(args) {
        this.selected = false;
        if (descriptor < 0 || args[4].toInt32() !== descriptor) return;
        event('mmap-request', {address: args[0].toString(), length: args[1].toString(),
            protection: args[2].toUInt32(), flags: args[3].toUInt32(), fd: args[4].toInt32(),
            offset: args[5].toString(), caller: relative(this.returnAddress)});
        if (!this.returnAddress.equals(stock.base.add(0x270284)) || !args[0].isNull() ||
            args[1].toUInt32() !== size || args[2].toUInt32() !== 3 || args[3].toUInt32() !== 1 ||
            !args[5].isNull() || region !== null) {
            event('unsupported-mmap', {completed: false});
            return;
        }
        args[2] = ptr(0); // PROT_NONE: no unknown register value is readable.
        args[3] = ptr(0x22); // Private anonymous transport, not a physical BAR.
        args[4] = ptr(-1);
        this.selected = true;
    },
    onLeave(result) {
        if (!this.selected) return;
        if (result.equals(ptr(-1)) || result.isNull()) {
            event('mapping-failed', {result: result.toString()});
            return;
        }
        // Frida recycles onLeave's return-value wrapper; retain the address value, not that wrapper.
        region = ptr(result.toString());
        event('mapping-ready', {base: region.toString(), length: size, backing_protection: '---',
            hardware_values_supplied: false});
    }
});
// NativeFunction calls can flush pending patches during setup. Never admit an open
// until both hooks and the exception handler are installed and ready together.
Interceptor.flush();
event('adapter-ready', {pid: Process.id, stock_module: stock.name, native_instructions_preserved: true});
armed = true;
