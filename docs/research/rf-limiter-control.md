# Fixed-frequency ordinary channel-limiter control

2026-10-01. The separately frozen
[OFF → 250M → OFF protocol](rf-limiter-control-protocol.md) completed all
fifteen scheduled RAW records at one fixed 975 MHz source command, five per
condition. Both OFF groups passed the unchanged default receive guard. The
five 250M records retained default receive rejections while passing independent
RAW geometry, count, rate, finite-voltage and upper-range qualification. The
condition-specific interpretation was preserved separately from each original
receive receipt. No received-frequency or level threshold was retrospectively
widened.

The controller began at 23:23:03.162 UTC; fresh capture was ready at
23:23:05.198. All fifteen records completed at 23:24:58.916. Scope restoration
completed at 23:25:09.985, and the recorder exited normally at 23:25:10.125.
The source received exactly one 975 MHz/raw-zero command and the planned
100 MHz/raw-zero return after all records completed, with no intergroup source
write. Both nine-byte driver-accepted frames matched their exact requests.
This is transport acceptance, not an invented source acknowledgment.

Independent offline verification matched all original waveform and preamble
bytes to their captured SCPI replies, recomputed all fifteen default and
condition receipts exactly, and bound each record to a distinct preceding
RUN/STOP sequence and the selected ordinary limit readback. All fifteen slots
are condition-eligible; none is missing. The complete capture contains 23,641
stored frames, zero reported kernel drops and graceful recorder exit zero.
Reassembled SCPI streams match 251 request files / 4,343 bytes and 194 response
files / 21,003,240 bytes, including both connection FINs. These checks do not
prove that every frame on the physical wire was retained.

The original 500 mV/div, 10 ns/div, 10k memory, OFF bandwidth limit, waveform
export configuration and running acquisition were restored and queried.
The temporary host address and lease helper were removed. Host network
preference and interface-mapping files were byte-identical before and after;
forwarding/NAT/sharing remained disabled and the normal default route separate.
No firmware, installed software policy, entitlement, calibration or wiring
change occurred. A live visual UI witness is not asserted by SCPI readbacks.

The acquisition was sealed and verified before final reduction. Private raw
evidence is retained under `out/rf/limiter-control-20261001T232500Z/`:
680 artifacts, 82,436,058 bytes; manifest SHA-256
`d405290e96aaf9046c7609d392ba5a42a92d5e68c71fa999226f66940156d04d`.
The frozen supplied-record condition helper passed 31 synthetic tests,
strict type/format/lint checks and independent CLI low-floor controls.

Final AC RMS evaluation is a separate decision task. Default receive rejection
in the middle condition alone is not the sensitivity verdict.
