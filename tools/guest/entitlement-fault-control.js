// Private-code ARM64 fault-recorder control in a fresh disposable guest process.
// No stock library loading or specimen-derived state is needed by this control.
'use strict';

const journal = new File('/data/local/tmp/entitlement/events.jsonl', 'w');
const options = { exceptions: 'steal', scheduling: 'cooperative' };
let sequence = 0;
const nativeExit = new NativeFunction(Module.findExportByName('libc.so', '_exit'),
    'void', ['int'], options);

function event(kind, details) {
    const payload = Object.assign({ kind: kind, sequence: ++sequence,
        stage: 'private-arm64-null-read' }, details || {});
    journal.write(JSON.stringify(payload) + '\n');
    journal.flush();
    send(payload);
}

function stop(kind, reason, code, details) {
    event(kind, Object.assign({ reason: reason, exit_code: code, terminal_ack: true }, details || {}));
    recv('terminal-ack', function () {}).wait();
    nativeExit(code);
}

setImmediate(function () {
    try {
        if (Process.arch !== 'arm64' || Process.pointerSize !== 8) {
            throw new Error('Control requires ARM64');
        }
        const code = Memory.alloc(Process.pageSize);
        if (!Memory.protect(code, Process.pageSize, 'r-x')) throw new Error('Code protection failed');
        // ldr x0, [x0]; ret. Only this newly allocated private page is changed.
        const bytes = [0x00, 0x00, 0x40, 0xf9, 0xc0, 0x03, 0x5f, 0xd6];
        Memory.patchCode(code, bytes.length, function (writable) { writable.writeByteArray(bytes); });
        const actual = Array.from(new Uint8Array(code.readByteArray(bytes.length)));
        if (actual.some((value, index) => value !== bytes[index])) throw new Error('Private code mismatch');
        const load = new NativeFunction(code, 'pointer', ['pointer'], options);
        event('control-call-enter', { expected_pc: code.toString(), instruction_bytes: '000040f9c0035fd6' });
        let caught = null;
        try {
            load(ptr(0));
        } catch (error) {
            caught = error;
        }
        if (caught === null) throw new Error('Null read returned without a native exception');
        const context = caught.context;
        const memory = caught.memory;
        const registers = {};
        if (context !== undefined && context !== null) {
            ['pc', 'lr', 'sp', 'fp'].concat(Array.from({ length: 29 }, (_, i) => 'x' + i))
                .forEach(function (name) {
                    if (context[name] !== undefined) registers[name] = context[name].toString();
                });
        }
        const details = {
            message: String(caught), exception_type: caught.type || null,
            expected_pc: code.toString(), observed_pc: registers.pc || null,
            memory_address: memory && memory.address ? memory.address.toString() : null,
            memory_operation: memory ? memory.operation : null, registers: registers
        };
        event('control-fault-caught', details);
        const verified = context !== undefined && context !== null && context.pc !== undefined &&
            context.pc.equals(code) && memory !== undefined && memory !== null &&
            memory.operation === 'read' && memory.address !== undefined && memory.address.isNull();
        if (!verified) {
            stop('failure', 'fault-control-context-mismatch', 78,
                Object.assign({ context_verified: false }, details));
            return;
        }
        stop('dependency-stop', 'fault-control-confirmed', 77,
            Object.assign({ context_verified: true }, details));
    } catch (error) {
        stop('failure', 'fault-control-script-error', 78, { message: String(error) });
    }
});
