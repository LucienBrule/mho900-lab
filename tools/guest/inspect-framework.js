// Frida's injected Java bridge requires JavaScript; this is diagnostic only.
'use strict';
Java.perform(function () {
    const manager = Java.use('com.android.server.pm.PackageManagerService');
    const setting = Java.use('com.android.server.pm.PackageSetting');
    const parsed = Java.use('android.content.pm.PackageParser$Package');
    console.log('framework-inspection-ready');
    for (const method of manager.class.getDeclaredMethods()) {
        const description = method.toString();
        if (/verifySignatures|compareSignatures/.test(description)) console.log(description);
    }
    for (const type of [setting, parsed]) {
        for (const field of type.class.getDeclaredFields()) console.log(field.toString());
    }
});
