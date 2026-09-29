#!/usr/bin/env python3
"""Exec an owned recorder with an explicit signal mask and dispositions.

This changes only the current child process. It does not change host policy.
The inherit mode exists solely for the host-only differential control.
"""
import argparse
import json
import os
from pathlib import Path
import signal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--signal-state", type=Path, required=True)
    parser.add_argument("--mode", choices=("normalize", "inherit"), default="normalize")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or not Path(command[0]).is_absolute():
        parser.error("an absolute executable path is required after --")

    before = sorted(int(s) for s in signal.pthread_sigmask(signal.SIG_BLOCK, []))
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, signal.SIG_DFL)
    if args.mode == "normalize":
        signal.pthread_sigmask(signal.SIG_SETMASK, [])
    after = sorted(int(s) for s in signal.pthread_sigmask(signal.SIG_BLOCK, []))
    with args.signal_state.open("x") as output:
        output.write(f"schema_version = 1\nmode = {json.dumps(args.mode)}\n")
        output.write(f"blocked_before = {before}\nblocked_after = {after}\n")
        output.write("int_term_hup_dispositions = \"default\"\n")
        output.flush()
        os.fsync(output.fileno())
    os.execv(command[0], command)


if __name__ == "__main__":
    main()
