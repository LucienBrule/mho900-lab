# Retained capture assessment

`mho-lab capture assess` reads a saved classic Ethernet pcap and saved tcpdump
stderr. It compares the structurally retained frame count with the final reported
capture count and requires zero reported kernel drops in every recognized group.
It never starts tcpdump or opens a network interface.

```sh
uv run --locked mho-lab capture assess out/example.pcap --stderr out/example.stderr
```

The underlying `mho-transport` library exposes `inspect_capture`,
`parse_tcpdump_statistics` and `assess_capture` separately. Structural inspection
uses the same bounded pcap reader as TCP reconstruction, but does not require a TCP
connection or validate the protocols inside each Ethernet frame. DHCP-only or
empty captures can therefore be assessed without pretending they contain a stream.

The statistics profile accepts UTF-8 text up to 1 MiB with a final newline.
Before statistics begin, startup text is retained but not interpreted. Recognized
inline interim groups have the tcpdump prefix and all three counts. The last group
must be three standalone lines, with no unexplained trailing text:

```text
3 packets captured
3 packets received by filter
0 packets dropped by kernel
```

Missing or partial groups, contradictory count progression, unexpected suffixes
and reported drops prevent acceptance. Missing statistics are never substituted
with zero. The reported count of packets received by the filter is preserved
without assuming that its relationship to processed packets is portable.

Successful CLI output is a TOML assessment containing input hashes and counts.
Rejection exits with status 1; invalid CLI arguments exit with status 2. Neither
path rewrites its inputs. Symlinked or special-file log inputs and observable
changes during their bounded read are rejected. Independent reads do not create
an atomic snapshot of the two inputs or authenticate that they belong to one run.

Acceptance establishes agreement between retained frame structure and the supplied
reported counts. Three separate questions remain:

- **Process exit:** a terminal-looking log is not proof that the owned recorder
  exited or was reaped. Process lifecycle evidence must establish that separately.
- **Drop reporting:** tcpdump can report zero when the operating system does not
  supply a drop counter. Backend support is not established by this parser.
- **Traffic completeness:** consistent counts do not prove that every packet on
  the segment reached the capture interface, nor do they establish host isolation.

The CLI emits explicit false flags for those unestablished claims. A useful capture
with missing terminal counts remains preserved evidence; it simply fails this
stronger finalization profile. Do not rewrite an old capture to make it pass.

The counter semantics follow the [tcpdump manual source](https://github.com/the-tcpdump-group/tcpdump/blob/master/tcpdump.1.in).
Experiment-specific controls still decide what protocol observations or device
behavior the retained packets support.
