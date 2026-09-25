// Frida's injected Java bridge requires JavaScript. No app code is instrumented.
'use strict';
Java.perform(function () {
    const manager = Java.use('com.android.server.pm.PackageManagerService');
    const exception = Java.use('com.android.server.pm.PackageManagerException');
    const digest = Java.use('java.security.MessageDigest');
    const stream = Java.use('java.io.FileInputStream');
    const file = Java.use('java.io.File');
    const verify = manager.verifySignaturesLP.overload(
        'com.android.server.pm.PackageSetting', 'android.content.pm.PackageParser$Package');
    const apkHash = '6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b';
    const stockSigner = 'f48e7189aac174df7fd19acf58b6d15832760fcf25ac0a6d4bcd5fc1974d4c03';
    const platformSigner = 'c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8';
    function hex(bytes) {
        return Array.from(bytes, b => ('0' + (b & 255).toString(16)).slice(-2)).join('');
    }
    function signer(signatures) {
        return signatures !== null && signatures.length === 1
            ? hex(digest.getInstance('SHA-256').digest(signatures[0].toByteArray())) : '';
    }
    function reason(setting, pkg) {
        if (String(pkg.packageName.value) !== 'com.rigol.scope') return 'package';
        if (String(pkg.mSharedUserId.value) !== 'android.uid.system') return 'requested-uid';
        const shared = setting.sharedUser.value;
        if (shared === null || String(shared.name.value) !== 'android.uid.system' ||
            shared.userId.value !== 1000 || setting.appId.value !== 1000) return 'assigned-uid';
        if (setting.pkg.value !== null) return 'existing-package';
        if (pkg.splitCodePaths.value !== null || pkg.childPackages.value !== null) return 'compound-package';
        if (signer(pkg.mSignatures.value) !== stockSigner) return 'signer';
        if (signer(shared.signatures.value.mSignatures.value) !== platformSigner) return 'platform-signer';
        const path = pkg.baseCodePath.value;
        const source = file.$new(path);
        const length = String(source.length());
        const modified = String(source.lastModified());
        const input = stream.$new(path);
        const hash = digest.getInstance('SHA-256');
        const buffer = Java.array('byte', new Array(65536).fill(0));
        try {
            let count;
            while ((count = input.read(buffer)) !== -1) hash.update(buffer, 0, count);
        } finally { input.close(); }
        if (length !== String(source.length()) || modified !== String(source.lastModified())) return 'file-changed';
        if (hex(hash.digest()) !== apkHash) return 'digest';
        return 'exact-stock';
    }
    verify.implementation = function (setting, pkg) {
        try {
            return verify.call(this, setting, pkg);
        } catch (original) {
            let rejection = 'unexpected-exception';
            try {
                if (original.$h !== undefined &&
                    Java.cast(original.$h, exception).error.value === -8) {
                    rejection = reason(setting, pkg);
                    if (rejection === 'exact-stock') {
                        const info = pkg.applicationInfo.value;
                        const previous = String(info.seinfo.value);
                        if (previous !== 'default' || info.uid.value !== 1000) {
                            throw new Error('Unexpected application label or UID');
                        }
                        info.seinfo.value = 'platform';
                        console.log('LABEL exact-stock uid=1000 before=' + previous + ' after=' + info.seinfo.value);
                        console.log('ADMIT exact-stock shared-user-error=-8');
                        return;
                    }
                }
            } catch (guardError) {
                console.log('GUARD-ERROR ' + guardError);
                rejection = 'guard-error';
            }
            console.log('REJECT ' + String(pkg.packageName.value) + ' reason=' + rejection);
            throw original;
        }
    };
    console.log('admission-exception-ready');
});
