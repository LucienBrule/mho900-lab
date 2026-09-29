// Compose this prelude before entitlement-baseline.js in a frozen run source.
// ART readiness: also prepend entitlement-art-readiness.js. No stock class or method is replaced.
'use strict';

function entitlementArtCheckJavaException(label) {
    try {
        // Pinned bridge Env.throwIfExceptionPending turns the pending throwable into a JS error.
        // It clears JNI state to format that error, but execution stops; the stock call never continues.
        Java.vm.getEnv().throwIfExceptionPending();
    } catch (error) {
        event('art-java-exception', { function: label, message: String(error), continuation: false });
        throw error;
    }
}

function entitlementArtStart(continueBaseline) {
    const readinessOnly = typeof entitlementArtReadinessOnly !== 'undefined' && entitlementArtReadinessOnly;
    const deadline = Date.now() + 10000;
    let attempt = 0;

    function fail(error) {
        stop('failure', 'art-component-error', 78,
            Object.assign({ message: String(error), stage: 'stock-api-jni-readiness' }, faultDetails(error)));
    }

    function prepare() {
        try {
            if (!Java.available) {
                if (Date.now() >= deadline) throw new Error('Actual Java VM did not become available');
                event('art-vm-wait', { attempt: ++attempt });
                setTimeout(prepare, 100);
                return;
            }
            Java.performNow(function () {
                try {
                    const ClassLoader = Java.use('java.lang.ClassLoader');
                    const loader = ClassLoader.getSystemClassLoader();
                    if (loader === null) throw new Error('No system application classloader');
                    Java.classFactory.loader = loader;
                    const Host = Java.use('lab.mho900.guest.EntitlementHost');
                    if (!Host.ready.value) {
                        if (Date.now() >= deadline) throw new Error('ART host main did not become ready');
                        event('art-host-wait', { attempt: ++attempt });
                        setTimeout(prepare, 100);
                        return;
                    }
                    currentCall = 'ART:load-stock-API';
                    event('art-host-ready', { readiness_only: readinessOnly,
                        host_class: 'lab.mho900.guest.EntitlementHost',
                        class_loader: String(loader.getClass().getName()) });
                    // The stock API static initializer is the real Java caller of System.loadLibrary.
                    // Its DT_NEEDED dependencies resolve through the pinned guest native-library path.
                    const Class = Java.use('java.lang.Class');
                    const apiClass = Class.forName('com.rigol.scope.cil.API', true, loader);
                    const loadedName = String(apiClass.getName());
                    if (loadedName !== 'com.rigol.scope.cil.API') throw new Error('Unexpected API class');
                    ['libc++_shared.so', 'libfftw3f.so', 'libscope-auklet.so'].forEach(function (name) {
                        const resolved = Process.getModuleByName(name);
                        const expected = LIB_DIRECTORY + name;
                        event('art-native-module', { name: name, path: resolved.path,
                            expected_path: expected, matches_fixture_path: resolved.path === expected,
                            base: resolved.base.toString(), size: resolved.size });
                        if (resolved.path !== expected) throw new Error('Native module resolved outside fixture: ' + name);
                    });
                    const module = Process.getModuleByName('libscope-auklet.so');
                    aukletModule = module;
                    const slots = [ ['java_vm', 0xbe0e38], ['api_class_global', 0xbe0e48],
                        ['redraw_method', 0xbe0e50], ['error_method', 0xbe0e58] ];
                    const references = {};
                    slots.forEach(function (entry) {
                        const value = module.base.add(entry[1]).readPointer();
                        if (value.isNull()) throw new Error('Stock JNI reference missing: ' + entry[0]);
                        references[entry[0]] = value;
                        event('stock-jni-reference', { name: entry[0], elf_va: '0x' + entry[1].toString(16),
                            value: value.toString(), source: 'unmodified-JNI_OnLoad' });
                    });
                    // Execute the stock wrapper on its actual registered VM; no fabricated VM/vtable.
                    const getEnv = native(module.name, '_ZN7_JavaVM6GetEnvEPPvi', 'int',
                        ['pointer', 'pointer', 'int']);
                    const output = Memory.alloc(Process.pointerSize);
                    output.writePointer(ptr(0));
                    const result = invoke('stock-JavaVM::GetEnv', getEnv,
                        [references.java_vm, output, 0x10004]);
                    const env = output.readPointer();
                    if (result !== 0 || env.isNull()) throw new Error('Actual stock VM GetEnv failed: ' + result);
                    const details = { stage: 'stock-api-jni-readiness', java_vm_verified: true,
                        api_class_loaded: true, stock_factory_called: false, get_env_return: result,
                        environment_present: true, class_global_present: true,
                        redraw_method_present: true, error_method_present: true,
                        callback_substitution: false };
                    event('art-jni-ready', details);
                    if (readinessOnly) {
                        stop('dependency-stop', 'art-readiness-confirmed', 77, details);
                        return;
                    }
                    // Remain on a genuinely attached ART thread through stock construction and callbacks.
                    continueBaseline();
                } catch (error) {
                    fail(error);
                }
            });
        } catch (error) {
            fail(error);
        }
    }
    prepare();
}
