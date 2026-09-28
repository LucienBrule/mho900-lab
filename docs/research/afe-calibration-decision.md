# AFE decision: preserve the contract and request factory-state evidence

The AFE static task is closed. Its normal loader pair needs filesystem state and
live calibration bytes, not another synthetic register response. The appropriate
observation boundary remains the whole pair, from unexecuted `0x333bac` to
unexecuted `0x333bdc`. There is no evidence here supporting a change to kernel or
emulator-device modeling, nor a reason to test each of the twelve object writes
in its own guest experiment.

The important uncertainty is now which calibration environment to represent.
The extracted corpus contains none of the four AFE files. The present guest
construction likewise supplies none, but that does not establish factory state.
Its root-owned `0755` data directory would ordinarily prevent UID 1000 from
creating the primary bandwidth file. Those conditions select a plausible guest
failure path, not necessarily the physical instrument's normal path.

Stock bandwidth loading unconditionally patches twelve words and attempts to
persist the entire 320-byte global record. Unknown entry bytes matter: a
successful write could serialize them, while a failed save is ignored by the
loader. Even a negative load status does not tell us whether persistence happened.
Choosing zeroes or adding write permission simply to advance initialization would
introduce a new unsupported model assumption.

A local missing-file experiment remains technically possible. It would answer
whether the stock pair follows the predicted failure path under the current
fixture. It would not answer which factory calibration records are required.
Because the operator explicitly requested a stop when physical evidence would
materially resolve uncertainty, no successor experiment is admitted here. This
is a completed decision with a precise evidence limitation, not a claim that
software analysis cannot progress without hardware.

## Exact bench question

For the untouched unit, with its firmware version and boot/application state
recorded, what are the earliest available contents and filesystem metadata of:

- `/rigol/data/cal_afe_zero.hex`
- `/rigol/data/default/cal_afe_zero.hex`
- `/rigol/data/cal_afe_bandwidth.hex`
- `/rigol/data/default/cal_afe_bandwidth.hex`

For each path, the requested record is presence or absence, file type/symlink
status, size, mode, owner/group, label, hash, and preserved bytes for local
checked-stream parsing. Include the containing directories' metadata and relevant
mount options. Check the 28-byte header, declared payload length, header CRC and
payload CRC; retain trailing bytes rather than normalize the record. Expected
payload sizes in the pinned `.26` implementation are 560 and 320 bytes.

Also record whether Sparrow had already run before collection. A primary bandwidth
file captured after startup may already have been created or rewritten by the
routine recovered here. It is then an observation of post-startup state, not
proof of as-shipped bytes. Do not reboot, relaunch, recalibrate, or alter the
instrument merely to reconstruct an unavailable pre-startup state under this
request. Physical collection itself remains outside this task's authorization.

The first question is file state, not analog calibration performance. If the unit
runs a different firmware version, preserve that distinction and compare its
loader implementation before treating the `.26` contract as authoritative.

## What the answer would decide

- Valid primary records would support a whole-pair prediction using observed
  per-unit files and the known unconditional bandwidth patch/save behavior.
- Default-only records would support explicit fallback loading with separately
  observed primary-directory write behavior.
- Missing or invalid records would make initial live object bytes and actual
  save outcome the next observation question; they would not justify invented
  calibration data.

Any later guest validation should bind the actual loader/global source pointers,
capture both payloads before and after, record file outcomes and process umask,
and maintain thread coverage. New device responses are unnecessary for the
recovered normal path. The existing observer remains a candidate implementation;
it has not been extended or qualified for this new region.
