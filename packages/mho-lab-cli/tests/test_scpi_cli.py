"""Offline query interpretation and deliberate identity disclosure controls."""

import os
import tomllib
from pathlib import Path

import pytest
from click.testing import CliRunner

from mho_lab_cli.cli import main


@pytest.mark.parametrize("disclose", [False, True])
def test_identity_is_opaque_and_disclosure_is_explicit(tmp_path: Path, disclose: bool) -> None:
    requests = tmp_path / "request.bin"
    replies = tmp_path / "reply.bin"
    requests.write_bytes(b"*IDN?\n:SYSTem:OPTion:STATus? BND\n")
    replies.write_bytes(b'Synthetic "Maker",Model\\X,PRIVATE-SERIAL,00.01.00\r\n0\n')
    arguments = ["scpi", "inspect", "--requests", str(requests), "--replies", str(replies)]
    if disclose:
        arguments.append("--show-identity")
    result = CliRunner().invoke(main, arguments)
    assert result.exit_code == 0, result.output
    document = tomllib.loads(result.output)
    assert document["query_count"] == 2
    assert document["physical_origin_proven"] is False
    assert ("PRIVATE-SERIAL" in result.output) is disclose
    if not disclose:
        assert "Synthetic" not in result.output and "Model" not in result.output
    assert ("00.01.00" in result.output) is disclose
    assert 'state = "0"' in result.output
    if disclose:
        assert 'manufacturer = "Synthetic \\"Maker\\""' in result.output


@pytest.mark.parametrize(
    "query_bytes,response",
    [
        (b"*RST\n", b"PRIVATE-SERIAL\n"),
        (b"*IDN?\n", b"PRIVATE-SERIAL\n"),
        (b"*IDN?\n", b"A,B,PRIVATE-SERIAL,D\n1\n"),
        (b":SYSTem:OPTion:STATus? BND\n", b"PRIVATE-SERIAL\n"),
    ],
)
def test_rejected_payloads_do_not_leak(tmp_path: Path, query_bytes: bytes, response: bytes) -> None:
    requests = tmp_path / "request.bin"
    replies = tmp_path / "reply.bin"
    requests.write_bytes(query_bytes)
    replies.write_bytes(response)
    result = CliRunner().invoke(
        main, ["scpi", "inspect", "--requests", str(requests), "--replies", str(replies)]
    )
    assert result.exit_code == 1
    assert "PRIVATE-SERIAL" not in result.output


@pytest.mark.parametrize("kind", ["symlink", "fifo", "oversized"])
def test_transcript_input_rejects_unbounded_or_indirect_files(tmp_path: Path, kind: str) -> None:
    requests = tmp_path / "request.bin"
    replies = tmp_path / "PRIVATE-PATH.bin"
    requests.write_bytes(b"*IDN?\n")
    if kind == "symlink":
        replies.symlink_to(requests)
    elif kind == "fifo":
        os.mkfifo(replies)
    else:
        replies.write_bytes(bytes(1024**2 + 1))
    result = CliRunner().invoke(
        main, ["scpi", "inspect", "--requests", str(requests), "--replies", str(replies)]
    )
    assert result.exit_code == 1
    assert "PRIVATE-PATH" not in result.output
    assert "input:" in result.output
