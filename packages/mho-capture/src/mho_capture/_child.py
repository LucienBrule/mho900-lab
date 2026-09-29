"""Private installed bootstrap. This is not a public command-line interface."""

import json
import os
import signal
import sys
import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator


class Launch(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    executable: str
    arguments: tuple[str, ...]
    witness: str

    @field_validator("arguments", mode="before")
    @classmethod
    def argument_array(cls, value: object) -> object:
        if isinstance(value, list):
            return tuple(value)
        return value


def bootstrap(path: Path) -> None:
    launch = Launch.model_validate(tomllib.loads(path.read_text()))
    before = sorted(int(s) for s in signal.pthread_sigmask(signal.SIG_BLOCK, []))
    dispositions_before = [
        str(signal.getsignal(sig)) for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
    ]
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, signal.SIG_DFL)
    signal.pthread_sigmask(signal.SIG_SETMASK, [])
    after = sorted(int(s) for s in signal.pthread_sigmask(signal.SIG_BLOCK, []))
    dispositions_after: list[int] = []
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        disposition = signal.getsignal(sig)
        if not isinstance(disposition, int):
            raise ValueError("signal disposition is not a normalized integer")
        dispositions_after.append(disposition)
    lines = [
        'schema = "mho-capture.child-signals/1"',
        f"pid = {os.getpid()}",
        "blocked_before = " + json.dumps(before),
        "blocked_after = " + json.dumps(after),
        'signal_names = ["SIGINT", "SIGTERM", "SIGHUP"]',
        "dispositions_before = " + json.dumps(dispositions_before),
        "dispositions_after = " + json.dumps(dispositions_after),
    ]
    descriptor = os.open(launch.witness, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write("\n".join(lines) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.execv(launch.executable, [launch.executable, *launch.arguments])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(64)
    bootstrap(Path(sys.argv[1]))
