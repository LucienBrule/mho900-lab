# RF source first-power and USB observation

2026-09-30. `TASK.rf.usb-first-contact` observed a working main screen and an enumerated USB serial interface
after the operator reported the source powered and connected through the dock. Both SMA connectors were visibly
unconnected in the supplied screen photograph. The exact power-on time and switch sequence were not reported.
No oscilloscope interaction occurred.

## Screen evidence

The first screen labels the synthesizer `PLL_IC:MAX2870`, displays a 470.00 MHz point frequency and highlights
`Point`. Sweep fields are 50.00 MHz start, 150.00 MHz stop and 1.00 MHz step. The highlight is consistent with
point output enabled according to the delivered leaflet; it is not an RF measurement. The screen does not show
output power, startup mode or reference-clock settings. It demonstrates an operating UI at the photographed
instant, not a timed stability test.

The firmware label and the [earlier RF-package marking](rf-source-internal-photo-review.md) are separate facts.
The label does not resolve the silicon identity, and the marking does not determine the serial command selector.

## Host evidence

Before connection, no USB serial-node pair was present in the saved serial-node inventory. After connection,
one new callout/dialin pair appeared. Detailed IORegistry ancestry ties it through `AppleUSBCHCOM` to the new
`USB Serial` device with VID `1a86`, PID `7523`, under the dock's USB hubs. The existing Apple DriverKit driver
is bound; no driver installation was needed. The target was not selected from a guessed path or vendor ID alone.

The device has no USB serial-number descriptor. Its current node suffix and location identify this connection,
not a durable unit identity. The exact path, location, device registry IDs, raw trees and screen image remain
private. Future serial operations must revalidate the target and stop if its identity/topology changes.

The initial structured registry capture omitted serial-client properties. A second capture with explicit
property output supplied the ancestry check; both are preserved. Repeated subtree appearances are deduplicated
by registry-entry identity. No serial endpoint was opened and no command bytes were transmitted.

## Disposition

First power and USB enumeration succeeded. Command compatibility, frequency/power accuracy, mute behavior,
longer-term stability and RF suitability remain untested. The bounded next decision is one source-only serial
point-command experiment with an offline-verified frame and operator UI observation. No broad protocol probing,
firmware work or RF connection is justified by enumeration alone.

Private baseline and connected phases are independently sealed and verified. Their manifest hashes are recorded
in the task receipt. The [first-contact procedure](rf-source-usb-first-contact.md) remains the executed scope.
