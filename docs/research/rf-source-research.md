# MAX2870 source families and measurement constraints

2026-09-30. Documentary conclusion for `TASK.rf.source-research`. The large touchscreen board described by
HawkRAO is the leading family match for the photographed source. Internal board revision, firmware, output behavior
and serial compatibility remain unverified. No power, USB, RF or instrument operation was performed.

This completes the source-documentation question in [phase A](rf-response-roadmap.md). It supplies arrival checks;
it does not close the inventory, preparation decision or physical qualification tasks. Private photographs,
purchase records, unit markings and inventory remain in ignored evidence. Public source hashes and locators are
in [the reference manifest](rf-source-references.toml).

## Keep the reference designs separate

**Touchscreen family.** The [HawkRAO control article][hawk-control] shows left-side USB-C, right-side RFout and MCLK
SMA connectors, a large touch display, and a chip-selector/point/sweep/settings UI. The photograph also contains a
company-like UI label; that alone does not authenticate the manufacturer. The author reports CH340 USB serial
control at 115200 baud, 8N1. This is firsthand evidence about that author's board, not a vendor protocol guarantee.

**Small OLED family.** The supplied two-page `LTDZ_23.5M-6000M` manual describes an STM32F103C8T6, a 0.96-inch
90-by-160 OLED, CH340G and directional buttons. Its page-2 serial protocol differs from HawkRAO's. Shared synthesizer
and USB-serial chips do not make the firmware protocols interchangeable.

**Official evaluation kit.** The [MAX2870/MAX2871 EV-kit guide][evkit], pages 1-2, describes a separate PC-controlled
board with a default 50 MHz reference, dedicated reference input and multiple RF outputs. It documents 3 dB pads
at its RF outputs. These are properties of the EV kit, not corrections to apply to an unidentified touchscreen unit.

**Chip and porting documentation.** The [MAX2870 datasheet][datasheet] establishes IC behavior under its stated test
conditions. Application note 5498 compares MAX2870 and ADF4350 registers and loop-filter design. Its discussion on
pages 7-8 explains why register/layout similarity is insufficient to establish equivalent PLL behavior. Neither
document identifies the commercial module or proves the installed chip, output network or firmware implementation.

**Delivered leaflet and photographs.** The operator-supplied photographs show the large screen, USB-C connector,
two SMA connectors and a plain rear cover. The accompanying leaflet is explicitly for a 2.8-inch touchscreen
source, matching that form factor rather than the OLED manual. Its illustrated UI is not a photograph of the
delivered device running. No internal IC marking or manufacturer provenance is established by these views.

The leaflet supplies additional documentary claims:

- Page 1 describes 5 V power and the second SMA as a fixed 25 MHz oscillator output, corroborating the candidate
  MCLK interpretation. It claims serial control, but the two photographed pages contain no byte-level protocol.
- Page 1 describes `Point` and `Sweep` as output-enabling controls, and the unusually named `Quite` as output mute.
  The `Stop` field is the sweep endpoint frequency; it is not the documented output-mute control.
- Page 2 distinguishes mode A, which starts muted, from mode B, which resumes the prior operating state.
  The delivered setting and actual mute behavior remain unknown.
- Page 2 distinguishes a nominal +5 dBm chip figure from approximately 0 dBm reported in an unspecified test.
  It gives no frequency, load or uncertainty for that result, so it is neither a calibration nor an output ceiling.

These photographs and their hashes are preserved privately. They strengthen family identification without proving
HawkRAO serial compatibility. No touchscreen action, calibration command or hardware modification was performed.

## Candidate protocols are incompatible

| Property | HawkRAO touchscreen report | Small OLED manual |
| --- | --- | --- |
| Transport | 115200 baud, 8N1; reported CH340 | 115200 baud; reported CH340G |
| Point frame | 11 bytes, starts `AD 01` | 9 bytes, starts `55 55` |
| Frequency fields | Reference in 100 Hz units; RF in kHz | Separate integer MHz and fractional thousandths |
| Frame ending | Sum of preceding bytes modulo 256 | `0D 0A` |
| Power code 1 | Nominal +5 dBm | Nominal -4 dBm |
| Power code 4 | Nominal -4 dBm | Nominal +5 dBm |

The two example checksums in the saved HawkRAO article are internally consistent: the point example has 11 bytes
and checksum `C3`; the sweep example has 18 bytes and checksum `88`. This is an offline byte check only. The sweep
heading says 1 MHz steps, but the decoded step field and following explanation specify 10 kHz. Preserve that
documentation discrepancy; do not silently convert it into a tested protocol.

HawkRAO's examples configure a 10 MHz reference because the author's unit was modified. The same article names
25 MHz as the nominal original oscillator. Copying the example's reference field onto an unmodified unit could
misprogram its frequency calculation. No bytes were sent, and no query/readback or reliable stop command has been
established for the delivered unit. The leaflet's `Quite` claim supplies a manual mute candidate, not a tested
serial stop command. CH340 presence alone would not establish protocol identity.

## MCLK and the reference clock

[HawkRAO's modification report][hawk-reference] explicitly describes MCLK as the original 25 MHz oscillator output.
That author's modification disconnects the onboard oscillator and repurposes the connection as an external input.
This provides a strong family-specific explanation of the connector, while its direction, drive level and loading
still require confirmation for the delivered board. Do not infer that a reference-frequency UI field turns an
unmodified output connector into an input.

The [follow-up report][hawk-reference-2] describes changed spectral behavior with different external references.
This reinforces the choice to retain the original oscillator for the first experiment. External reference conversion
is separate research, not a prerequisite for the policy-response comparison.

## Consequences for measurement design

1. **Choose a usable common-source reference.** The IC's RF span begins at approximately 23.5 MHz. Its ability to
   accept a 10 MHz reference clock is a different property. A 50 or 100 MHz RF reference point is a candidate to
   qualify, not a claim of flat response. Do not splice in an unrelated clock to preserve the older 10 MHz anchor.
2. **Use fixed frequencies first.** The [element14 firsthand review][review] reports sweep endpoint/step bugs and
   retained settings. Its experience does not prove the delivered firmware behaves identically. Fixed points with
   observed settling avoid making sweep timing part of the first comparison. Datasheet lock time also depends on
   configuration and the loop filter; a seller's minimum dwell is not a qualification result.
3. **Measure fundamental response.** The review reports a harmonic-rich waveform and differences between labeled
   and measured power. The chip's power specifications also have output-network and test conditions. Preserve
   spectral ambiguity, source stability, actual amplitude and path effects rather than treating a screen setpoint
   as calibrated delivered power. At high frequency, explicitly assess aliases of source harmonics before accepting
   a sine fit; at 1 GHz sampled at 4 GSa/s, a 3 GHz harmonic can alias onto the fundamental. A small fit residual is
   not sufficient to rule that out. Filtering or independent spectral evidence may be needed for the chosen claim.
4. **Keep the first path simple.** Use a verified nominal-50-ohm cable/termination arrangement and an explicit level
   budget. The private connector review identified a BNC tee among available adapter types. A tee is not a matched
   splitter; two ideal 50-ohm loads in parallel present 25 ohms. Do not add a spare branch to the first path.
5. **Keep automation optional.** The CH340 report makes direct workstation control plausible without replacing the
   MCU. Qualify manually first, then add a small typed serial implementation only if it saves measurement effort.
   A successful serial write would not independently prove that the source reached the requested RF state.

The existing evaluation plan records the MHO900 datasheet's 50-ohm input conditions and 5 Vrms maximum, and proposes
a much smaller 200 mVpp signal at the connector. Those limits do not establish the module's output level or DC
behavior. Confirm native 50-ohm termination, the actual cable/pad chain and the source level before integration;
the source's nominal power setting and an adapter's mechanical fit are insufficient checks.

The element14 board was powered by USB-A to USB-C; the author reports USB-C to USB-C did not work on that example.
This is a useful arrival check, not a universal USB-C rule. The supplied cable and power markings should be checked
before first power. Automatic restoration of prior output remains possible; begin with RF isolated from the scope.

## Arrival checks and decision boundary

- Compare the actual connector layout, external markings and first UI with the candidate family. No disassembly
  is required for an initial family match. Preserve uncertainty about internal revision and authenticity.
- Confirm the supply arrangement, actual startup/output state, available level controls and nominal reference
  setting and mode A/B. Check the documented `Quite` mute behavior; a control label alone does not establish zero
  output. Do not confuse the sweep endpoint `Stop` field with mute.
- Keep MCLK unused during the first RF test. Confirm its electrical role before any later reference connection.
- Confirm which pads, terminations and independent measurement tools are on hand; qualify the output level, DC
  behavior and spectral/alias limitations using the available equipment and the proposed claim scope.
- Under an accepted pilot procedure, validate single-channel acquisition and full waveform export, fixed-point
  settling/repeatability and the data required to compare stock and derived policy.
- If serial automation is later admitted, identify the target interface, verify a bounded point command against
  the actual UI and RF observation, and keep incompatible protocols distinct. No blind sweep of serial ports.

The source is a plausible tool for a bounded relative experiment. Absolute 1 GHz bandwidth remains conditional on
the reference-plane amplitude and uncertainty evidence in the [RF evaluation plan](rf-performance-evaluation-plan.md).
Source-family identification and source qualification are separate outcomes. The next roadmap work remains the
inventory and preparation decision before physical integration.

[hawk-control]: https://sites.google.com/view/hawkrao/miscellaneous-sub-projects/software-control-of-max2870-lcd-signal-generator
[hawk-reference]: https://sites.google.com/view/hawkrao/miscellaneous-sub-projects/modifying-signal-generator-to-external-reference-part-i
[hawk-reference-2]: https://sites.google.com/view/hawkrao/miscellaneous-sub-projects/modifying-signal-generator-to-external-reference-part-ii
[review]: https://community.element14.com/technologies/test-and-measurement/b/blog/posts/using-a-max2870-frequency-synthesizer-signal-generator
[datasheet]: https://www.analog.com/media/en/technical-documentation/data-sheets/MAX2870.pdf
[evkit]: https://www.analog.com/media/en/technical-documentation/data-sheets/MAX2870EVKIT.pdf
