"""Exercise offline capture assessment without a network or TCP connection."""

from pathlib import Path

from click.testing import CliRunner

from mho_lab_cli.cli import main


def write_arp_capture(path: Path) -> None:
    header = (
        b"\xd4\xc3\xb2\xa1\x02\x00\x04\x00"
        + bytes(8)
        + (262144).to_bytes(4, "little")
        + (1).to_bytes(4, "little")
    )
    frame = bytes(12) + b"\x08\x06" + bytes(28)
    record = bytes(8) + len(frame).to_bytes(4, "little") * 2 + frame
    path.write_bytes(header + record * 3)


def test_structural_capture_assessment_needs_no_tcp(tmp_path: Path) -> None:
    path = tmp_path / "arp.pcap"
    write_arp_capture(path)
    stderr = tmp_path / "recorder.stderr"
    stderr.write_text(
        "tcpdump: 0 packets captured, 0 packets received by filter, 0 packets dropped by kernel\n"
        "3 packets captured\n3 packets received by filter\n0 packets dropped by kernel\n"
    )
    result = CliRunner().invoke(main, ["capture", "assess", str(path), "--stderr", str(stderr)])
    assert result.exit_code == 0, result.output
    assert "capture_frames = 3\n" in result.output
    assert "statistics_groups = 2\n" in result.output
    assert "process_exit_proven = false\n" in result.output
    assert "wire_completeness_proven = false\n" in result.output


def test_frame_count_mismatch_is_not_accepted(tmp_path: Path) -> None:
    path = tmp_path / "arp.pcap"
    write_arp_capture(path)
    stderr = tmp_path / "recorder.stderr"
    stderr.write_text(
        "2 packets captured\n2 packets received by filter\n0 packets dropped by kernel\n"
    )
    result = CliRunner().invoke(main, ["capture", "assess", str(path), "--stderr", str(stderr)])
    assert result.exit_code == 1
    assert "assessment/" in result.output


def test_missing_statistics_is_not_zero_drops(tmp_path: Path) -> None:
    path = tmp_path / "arp.pcap"
    write_arp_capture(path)
    stderr = tmp_path / "recorder.stderr"
    stderr.write_text("tcpdump: listening on a synthetic interface\n")
    result = CliRunner().invoke(main, ["capture", "assess", str(path), "--stderr", str(stderr)])
    assert result.exit_code == 1
    assert "statistics/" in result.output


def test_statistics_symlink_rejected(tmp_path: Path) -> None:
    path = tmp_path / "arp.pcap"
    write_arp_capture(path)
    original = tmp_path / "original.stderr"
    original.write_text(
        "3 packets captured\n3 packets received by filter\n0 packets dropped by kernel\n"
    )
    stderr = tmp_path / "linked.stderr"
    stderr.symlink_to(original)
    result = CliRunner().invoke(main, ["capture", "assess", str(path), "--stderr", str(stderr)])
    assert result.exit_code == 1
    assert "input/" in result.output
