// Actual stock cached-state queries for a disposable, explicitly derived native-library comparison.
// No installer, hardware programming, or option-query substitution is performed here.
'use strict';
function entitlementCapabilityPrepare(module, cfg, emit, invokeStock) {
    const arm = cfg.capability_arm;
    const expected = arm === 'stock' ? 17 : 18;
    const expectedOffset = arm === 'stock' ? '0x151b7a0' : '0x151b850';
    if (cfg.capability_experiment !== true || !['stock', 'derived'].includes(arm) ||
        cfg.expected_bandwidth_enum !== expected || cfg.expected_record_offset !== expectedOffset ||
        cfg.model !== 'MHO984') throw new Error('Invalid capability arm contract');
    function guarded(offset, bytes, result, args) {
        return checkedLocalFunction(module, offset, bytes, result, args);
    }
    // Check all original entry bytes before installing the parser observer.
    const getModel = guarded(0x429cbc, 'ff8301d1fd7b05a9fd43019148d03bd5', 'int', ['pointer', 'pointer']);
    const getRaw = guarded(0x429b40, 'ff4300d1283b0090089147f909008052', 'int', ['pointer', 'pointer']);
    const getEffective = guarded(0x429b10, 'ff4300d1283b0090084941f909008052', 'int', ['pointer', 'pointer']);
    const parseOption = guarded(0x429b70, 'ffc300d1fd7b02a9fd83009108008052', 'void', []);
    const ctor = guarded(0x239014, 'ff8300d1fd7b01a9fd430091e00700f9', 'void', ['pointer', 'pointer']);
    const dtor = guarded(0x239040, 'ff8300d1fd7b01a9fd430091e00700f9', 'void', ['pointer']);
    const cstr = guarded(0x235978, 'ff8300d1fd7b01a9fd430091e00700f9e00740f90a000094', 'pointer', ['pointer']);
    const parserAddress = requiredExport(module.name, '_ZN11CApiUtility21ApiUtility_ParseModelERK7RStringP9Bandwidth');
    if (!parserAddress.equals(module.base.add(0x42943c))) throw new Error('Unexpected parser entry');
    const selected = [];
    listeners.push(Interceptor.attach(parserAddress, {
        onEnter() { this.capture = currentCall === 'ApiUtility_SetModel'; },
        onLeave(result) {
            if (!this.capture) return;
            if (result.isNull()) throw new Error('Capability parser returned null');
            // Frida recycles retval objects; retain an owned NativePointer value.
            const retained = ptr(result.toString());
            selected.push(retained);
            emit('capability-parser-return', { arm: arm, selected_record_offset: retained.sub(module.base).toString(),
                observed_in: 'ApiUtility_SetModel', behavior_replaced: false, return_value_copied: true });
        }
    }));
    function selectedRecord() {
        if (selected.length !== 1) throw new Error('Expected one observed model-parser return');
        const row = selected[0];
        const offset = row.sub(module.base).toString();
        if (offset !== expectedOffset) throw new Error('Unexpected selected model row');
        const name = invokeStock('capability:selected-row-name', cstr, [row]).readUtf8String();
        const result = { arm: arm, selected_record_offset: offset, selected_record_name: name,
            selected_record_bandwidth_enum: row.add(24).readS32(), channels: row.add(28).readU32(),
            domain: row.add(32).readU32(), series: row.add(36).readU32() };
        emit('capability-selected-record', result);
        if (name !== (arm === 'stock' ? 'MHO984' : 'MHO984D') ||
            result.selected_record_bandwidth_enum !== expected || result.channels !== 4 ||
            result.domain !== 8 || result.series !== 900) throw new Error('Selected record contract differs');
        return result;
    }
    function observe(utility, stage) {
        const model = Memory.alloc(24), raw = Memory.alloc(4), effective = Memory.alloc(4);
        invokeStock('capability:RString-ctor', ctor, [model, Memory.allocUtf8String('')]);
        let result;
        try {
            const modelStatus = invokeStock('capability:GetModel:' + stage, getModel, [utility, model]);
            const rawStatus = invokeStock('capability:GetModelBw:' + stage, getRaw, [utility, raw]);
            const effectiveStatus = invokeStock('capability:GetBw:' + stage, getEffective, [utility, effective]);
            const identity = invokeStock('capability:model-c_str', cstr, [model]).readUtf8String();
            result = { arm: arm, stage: stage, model: identity, raw_bandwidth_enum: raw.readS32(),
                effective_bandwidth_enum: effective.readS32(), model_status: modelStatus, raw_status: rawStatus,
                effective_status: effectiveStatus, selected_record_offset: selected[0].sub(module.base).toString() };
            emit('capability-observation', result);
        } finally { invokeStock('capability:RString-dtor', dtor, [model]); }
        return result;
    }
    return {
        selectedRecord: selectedRecord,
        evaluate: function (utility) {
            const before = observe(utility, 'before-option-policy');
            emit('capability-option-policy-enter', { arm: arm, actual_stock: true });
            invokeStock('capability:ApiUtility_ParseOption', parseOption, []);
            emit('capability-option-policy-return', { arm: arm, returned: true, return_type: 'void' });
            const after = observe(utility, 'after-option-policy');
            const checks = {
                capability_identity_preserved: before.model === 'MHO984' && after.model === 'MHO984',
                capability_bandwidth_selected: before.raw_bandwidth_enum === expected && before.effective_bandwidth_enum === expected,
                capability_record_selected: selected.length === 1 && before.selected_record_offset === expectedOffset,
                capability_option_policy_preserved: after.raw_bandwidth_enum === expected && after.effective_bandwidth_enum === expected,
                capability_queries_succeeded: [before, after].every(x => x.model_status === 0 && x.raw_status === 0 && x.effective_status === 0)
            };
            emit('capability-evaluation', { arm: arm, before: before, after: after, expected_checks: checks });
            return checks;
        }
    };
}
