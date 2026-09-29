# Physical storage classification correction

During raw acquisition, the specimen's kernel reported `/sys/class/block/mmcblk0/device/type` as `SD` and its
product name as `MSSD0`. This supersedes the earlier eMMC assumption. A Linux `mmcblk0` device name identifies the
block-device family and is not sufficient to distinguish SD from MMC/eMMC.

The observed source remains `/dev/block/mmcblk0`, with 61132800 sectors of 512 bytes, or 31299993600 bytes. The
same sixteen partition extents and by-name relationships apply. The correction changes interpretation of the
storage/boot architecture, not the validity of the already authorized whole-device reads. Acquisition continues
with the same source, exact size, read-only commands, isolation, and preservation requirements.

This is a kernel-reported card classification. The enclosure was not opened, and physical packaging or removability
was not inspected. No hidden eMMC boot/RPMB area is claimed or sought. Future full-image emulation should reconcile
this evidence before choosing a storage-controller presentation.

Private evidence is `metadata/storage-type.stdout`, its command/error records, and `storage-class-decision.toml`
in `out/physical/mho984-raw-acquisition-20260929T032542Z`. The original first read remains unmodified and read-only;
its hash and byte count are unchanged. The task contract was revised through taskctl, retaining immutable history.
