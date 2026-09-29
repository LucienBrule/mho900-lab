// Observe original stock consumers for the private acquired-input disposable fixture only.
// No arguments, results, branch decisions, or stock bytes are replaced here.
'use strict';

function entitlementObserveConsumer(mod, emit, cfg) {
    if (cfg.physical_contact !== false || cfg.specimen_key_files_used !== true ||
        cfg.schema_version !== 'mho900-lab.acquired-option-fixture/1' ||
        cfg.acquired_option_experiment !== true || cfg.acquired_combined_experiment !== true ||
        cfg.capability_experiment !== true || !['stock','derived'].includes(cfg.capability_arm) ||
        cfg.acquired_catalog_experiment === true || cfg.acquired_capability_experiment === true ||
        cfg.catalog_candidate !== undefined || cfg.option_type !== undefined ||
        cfg.aes_key_ascii.length !== 32 || cfg.stock_native_sha256 !== STOCK_AUKLET_SHA256 || Process.arch !== 'arm64')
        throw new Error('Acquired observer fixture mismatch');
    const stacks = new Map();
    let invocation = 0;
    const maximumInvocations = 32;
    const maximumBlocks = 3;

    function hex(pointer, length) {
        return Array.from(new Uint8Array(pointer.readByteArray(length)),
            value => ('0' + value.toString(16)).slice(-2)).join('');
    }
    function guardedExport(name, offset, expected) {
        const address = requiredExport(mod.name, name);
        if (!address.equals(mod.base.add(offset)) || hex(address, expected.length / 2) !== expected) {
            throw new Error('Consumer observer stock guard mismatch: ' + name);
        }
        return address;
    }
    const verify = guardedExport('_ZN11CApiLicense12verifyOptionEP8COptInfoR7RStringS3_',
        0x437384, 'fc0f1ef8fd7b01a9fd430091ff830cd1');
    const decode = guardedExport('_Z14API_SetStr2Hex7RStringPcRi',
        0x242fe8, 'ff0301d1fd7b03a9fdc30091a1831ff8');
    const setKey = guardedExport('AES_set_decrypt_key',
        0x3ea328, 'ff8301d1fd7b05a9fd43019148d03bd5');
    const decrypt = guardedExport('AES_decrypt',
        0x3eb2b8, 'ff0303d1fc6f07a9fa6708a9f85f09a9');
    [[0x4375d0, 'd484f797'], [0x4375f4, 'df12f797'], [0x437638, '567df797']]
        .forEach(function (item) {
            if (hex(mod.base.add(item[0]), 4) !== item[1]) {
                throw new Error('Consumer observer call-site guard mismatch');
            }
        });

    function fail(message) {
        stop('failure', 'consumer-observer-contract', 78, { message: message });
    }
    function context(threadId, returnAddress, expectedReturn) {
        if (!returnAddress.equals(mod.base.add(expectedReturn))) return null;
        const stack = stacks.get(threadId);
        if (stack === undefined || stack.length === 0) {
            fail('Stock consumer call without an observed verifyOption invocation');
            return null;
        }
        return stack[stack.length - 1];
    }
    function record(kind, ctx, details) {
        emit(kind, Object.assign({ consumer_invocation: ctx.id, thread_id: ctx.threadId,
            consumer_call: ctx.call, option_type: ctx.optionType,
            encoding: 'conventional-byte-hex', observational_only: true }, details));
    }
    listeners.push(Interceptor.attach(verify, {
        onEnter: function (args) {
            if (++invocation > maximumInvocations) {
                fail('Stock consumer invocation limit exceeded');
                return;
            }
            const stack = stacks.get(this.threadId) || [];
            if (stack.length >= 2) {
                fail('Unexpected nested stock validation depth');
                return;
            }
            this.observed = { id: invocation, threadId: this.threadId, call: currentCall,
                optionType: args[1].readS32(), blocks: 0, schedule: null, keyHex: null };
            stack.push(this.observed);
            stacks.set(this.threadId, stack);
            record('consumer-verify-enter', this.observed, {});
        },
        onLeave: function (result) {
            if (this.observed === undefined) return;
            const stack = stacks.get(this.threadId);
            if (stack === undefined || stack.pop() !== this.observed) {
                fail('Stock consumer invocation stack mismatch');
                return;
            }
            record('consumer-verify-return', this.observed,
                { valid: (result.toInt32() & 1) !== 0, decrypt_blocks: this.observed.blocks });
        }
    }));
    listeners.push(Interceptor.attach(decode, {
        onEnter: function (args) {
            this.observed = context(this.threadId, this.returnAddress, 0x4375d4);
            if (this.observed === null) return;
            this.output = args[1];
            this.length = args[2];
        },
        onLeave: function () {
            if (this.observed === null) return;
            const count = this.length.readS32();
            if (count !== 32 && count !== 48) {
                fail('Stock hex decoder output outside bounded token sizes');
                return;
            }
            record('consumer-hex-decoded', this.observed,
                { byte_count: count, ciphertext_hex: hex(this.output, count) });
        }
    }));
    listeners.push(Interceptor.attach(setKey, {
        onEnter: function (args) {
            this.observed = context(this.threadId, this.returnAddress, 0x4375f8);
            if (this.observed === null) return;
            if (args[1].toInt32() !== 256) {
                fail('Stock AES consumer requested an unexpected key size');
                return;
            }
            this.observed.keyHex = hex(args[0], 32);
            this.observed.schedule = args[2];
        },
        onLeave: function (result) {
            if (this.observed === null) return;
            record('consumer-aes-key', this.observed,
                { bits: 256, key_hex: this.observed.keyHex, result: result.toInt32() });
        }
    }));
    listeners.push(Interceptor.attach(decrypt, {
        onEnter: function (args) {
            this.observed = context(this.threadId, this.returnAddress, 0x43763c);
            if (this.observed === null) return;
            if (++this.observed.blocks > maximumBlocks || this.observed.schedule === null ||
                !args[2].equals(this.observed.schedule)) {
                fail('Stock AES block count or schedule differs from observed consumer key');
                return;
            }
            this.block = this.observed.blocks - 1;
            this.inputHex = hex(args[0], 16);
            this.output = args[1];
        },
        onLeave: function () {
            if (this.observed === null) return;
            record('consumer-aes-block', this.observed, { block_index: this.block,
                byte_count: 16, ciphertext_hex: this.inputHex,
                plaintext_hex: hex(this.output, 16), schedule_matches_key: true });
        }
    }));
    emit('consumer-observer-installed', { maximum_invocations: maximumInvocations,
        maximum_blocks_per_invocation: maximumBlocks, stock_call_sites_guarded: true,
        physical_contact: false, acquired_material: true, observational_only: true });
    Interceptor.flush();
}
