# RF source USB first contact

2026-09-30. The operator prefers workstation control and asks whether to connect the delivered source by USB
or remove the display ribbon to identify the MCU. Choose USB first power with the ribbon intact. This narrow
source-only branch can establish transport availability before the full RF measurement inventory is resolved.
It does not qualify the RF output or authorize an instrument connection.

The [internal photographs](rf-source-internal-photo-review.md) show a CH340N-marked bridge. The
[candidate protocol research](rf-source-research.md) provides a plausible later control route. Further
disassembly and MCU identification are unnecessary for the immediate host-interface question.

## First transition

1. Preserve the host's USB registry, serial registry and serial device-node inventory with local and UTC times.
   Read these through macOS registry tools; do not open or probe serial ports.
2. Ask the operator to keep the ribbon connected, support the board on a clean nonconductive surface, and keep
   both RF OUT and MCLK unconnected, with no antenna. Leave the physical oscilloscope unchanged.
3. With the source switch OFF, connect the supplied USB-A to USB-C cable from a dock USB-A port to the source.
   Then switch the source ON if it has not already started. Record if connection itself starts the display.
4. Ask the operator to report connection and provide the first screen, without changing touchscreen settings.
   The source may restore a saved output state. The board is deliberately isolated from any RF load or receiver.
5. On confirmation, preserve the same host inventories again. Associate any new USB and serial identity through
   registry topology, vendor/product information and the before/after difference; do not guess a device path.
6. Record startup indications separately from observed USB identity. No UI indication proves an RF level,
   frequency, spectral quality or effective mute. Seal the phase before selecting a serial-control experiment.

Stop on abnormal heating, smell, repeated restarts or failure to start. The operator should remove USB power for
an electrical fault. A transport failure without those symptoms is evidence for the decision task, not a reason
to install drivers or change firmware automatically. Record all actual physical transitions reported.

## Subsequent decision

`TASK.rf.usb-control-decision` may select one compatibility experiment after stable startup and positive target
identification. Prepare its encoder and checksum offline, preserve exact bytes and account for control-line
effects when opening the serial port. Resolve the nominal reference setting before any point command. A source
UI response can validate command interpretation; actual RF response still requires the later integration checks.

No serial open/write, firmware upload, EEPROM operation, display calibration, programming connection or scope
operation belongs to this first-contact task. Keep raw host device identities and photographs in ignored evidence.
