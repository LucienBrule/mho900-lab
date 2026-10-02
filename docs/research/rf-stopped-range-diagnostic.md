# One stopped waveform after the initial range stop

The operator authorized continued investigation after the
[first matched-comparison abort](rf-policy-comparison-first-range-stop.md).
The next question concerns the actual waveform at nominal 100 MHz, before
another policy comparison is designed.

The running-scope built-ins exceeded the original ±180 mV guard and reported
a frequency different from the source request. They were separate queries,
without a stopped RAW record. A wider display range and one coherent record
can distinguish a range problem from a waveform or periodicity problem.

The [diagnostic contract](../../experiments/rf-stopped-range/contract.toml)
declares one source attempt and one fresh stopped RAW acquisition at 100 mV/div,
with the same cable and 50 Ω/DC/1×/zero/FULL input configuration. It retains
100,000 points at measured 4 GSa/s, equal preambles and all original bytes.
Strict ±360 mV extrema and 720 mV peak-to-peak bounds reserve ten percent of
the nominal ±400 mV display half-span. These are diagnostic criteria, separate
from the original comparison's range and qualification.

The unchanged receive profile is reported even if it rejects the larger signal.
A separately pinned diagnostic profile may assess periodicity after applying
the declared wider range. Neither result supplies an original comparison slot
or establishes a calibrated source fundamental. The original numerical contract
and all missing A1/B/A2 slots remain preserved.

Preparation must independently verify exact inherited capture, isolation,
owned transport, lease, epoch and restoration behavior. Execution requires a
fresh concrete control inventory and current stock process continuity. The
complete actual initial ordinary and export settings are restored while framing
is healthy. No native transition, reboot, entitlement, calibration or wiring
change belongs to this diagnostic.

The decision closes the question that was actually asked. A usable record may
support a newly declared matched comparison with common settings across all
arms. Rejected or missing samples preserve the uncertainty and identify the
smallest distinct next question. Neither outcome changes the completed failed
run, admits an unchanged retry, or proves continuous analog bandwidth.
