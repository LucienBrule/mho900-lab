# Physical FRAM baseline acquisition

The first stored-image attempt stopped at adapter metadata validation, before
staging or executing the FRAM reader. Its fresh stock private-cache observation
passed, but the specimen's older `stat` implementation rejects `-L` and does not
implement the requested device-number format specifiers. The controller preserved
that failure rather than guessing the device identity or weakening its gate.

This was a metadata-tool compatibility failure, not a FRAM transfer failure.
No direct FRAM transaction, option installation or capability change occurred.
The scope-facing capture contains 43,031 complete frames and zero kernel drops;
recorder exit was graceful. Temporary host networking was removed and the saved
network preference files match their baseline bytes.

The private run `mho984-fram-baseline-20260929T171200Z` is sealed with manifest
SHA-256 `4c3a71570a2662187cf5d7f3a4bd90b8caf5062ebe42607cc0e89fd8206fc43d`.
Its capture SHA-256 is
`929e18014b267b722008b85436a417cd8c423e4bd80dd3b074465e036fab1874`.

The next bounded correction is a native metadata-only probe using ARM64 stat
semantics, tested in the disposable guest. It should follow the exact stock
process descriptor and compare it with the device node and sysfs adapter,
without opening the device or issuing an ioctl. A new acquisition run may proceed
only after that correction is validated; the original failure remains immutable.

The normal-APK loader control independently establishes a candidate signed-APK-
preserving deployment method in the guest. That does not waive the stored-state
preservation requirement before physical option installation.

## Native-metadata acquisition: accepted

A fresh run, `mho984-fram-native-20260929T172406Z`, bound the stock CFram
process descriptor to its character-device node and `rk3x-i2c` adapter through
native stat results and sysfs metadata. Fresh independently verified cache-owner
observations bracket the acquisition. Process, boot, module and file identities
remained consistent.

Both 8192-byte images are byte-identical, SHA-256
`f939b16ca141447c7d413a04b330ddfa4ad10c333d2c7c358f423d2bf80d4a1b`.
All 1024 combined two-message transactions returned exactly 2. Independent replay
of the raw transaction journal reconstructs both images exactly. The stored
204-byte private stream matches the captured working/reference caches, including
saved-time record 16192 and encrypted-key-backup record 2337. Payloads remain private.

Remote shell wait evidence proves the helper exited normally. The capture has
46,567 complete frames and zero kernel drops; recorder exit was graceful. The
host address and responder were removed and saved network preferences are
byte-identical to baseline. Before/after screen captures show the normal
oscilloscope UI without a new prompt. They are discrete observations, not a
continuous visual recording.

| Artifact | SHA-256 |
| --- | --- |
| Raw transaction journal | `7704de2c1b0ddcf32feb38ff3768e8b113495836aa0f0f92e626673cd145d555` |
| Packet capture | `03475d423acba54b76084853bb55b421f53f1752bb805e9e05d6c4bd184479eb` |
| Complete 481-member evidence manifest | `cd7e012fab191b21d520359a15ce6593ae7081726b96415b9fbcf725164f4b35` |

This closes the missing stored-FRAM baseline for the authorized installation
sequence. It does not prove an atomic whole-device snapshot, power-loss behavior
or a tested FRAM restore procedure. No stored-data write, option installation,
capability deployment or reboot occurred in this acquisition.
