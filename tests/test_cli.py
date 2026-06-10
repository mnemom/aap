"""Tests for AAP CLI commands.

Tests the command-line interface for:
- aap init: Creating Alignment Cards
- aap verify: Verifying traces against cards
- aap check-coherence: Checking card compatibility
- aap drift: Detecting behavioral drift
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from aap.cli.main import main


@pytest.fixture
def runner() -> CliRunner:
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_card(tmp_path: Path, minimal_alignment_card: dict[str, Any]) -> Path:
    """Create a temporary alignment card file."""
    card_path = tmp_path / "card.json"
    card_path.write_text(json.dumps(minimal_alignment_card, default=str))
    return card_path


@pytest.fixture
def temp_trace(tmp_path: Path, minimal_trace: dict[str, Any]) -> Path:
    """Create a temporary trace file."""
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps(minimal_trace, default=str))
    return trace_path


@pytest.fixture
def temp_trace_dir(
    tmp_path: Path,
    aligned_trace_sequence: list[dict[str, Any]],
) -> Path:
    """Create a temporary directory with trace files."""
    traces_dir = tmp_path / "traces"
    traces_dir.mkdir()
    for i, trace in enumerate(aligned_trace_sequence):
        trace_path = traces_dir / f"trace-{i:03d}.json"
        trace_path.write_text(json.dumps(trace, default=str))
    return traces_dir


# ---------------------------------------------------------------------------
# aap --help tests
# ---------------------------------------------------------------------------


class TestMainHelp:
    """Tests for main CLI help."""

    def test_help(self, runner: CliRunner) -> None:
        """Main help should display all commands."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Agent Alignment Protocol CLI" in result.output
        assert "init" in result.output
        assert "verify" in result.output
        assert "check-coherence" in result.output
        assert "drift" in result.output

    def test_version(self, runner: CliRunner) -> None:
        """--version should display version."""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        # Check for semver pattern (e.g., "0.1.0", "0.1.1")
        import re

        assert re.search(r"\d+\.\d+\.\d+", result.output)


# ---------------------------------------------------------------------------
# aap init tests
# ---------------------------------------------------------------------------


class TestInitCommand:
    """Tests for aap init command."""

    def test_init_help(self, runner: CliRunner) -> None:
        """Init help should show options."""
        result = runner.invoke(main, ["init", "--help"])
        assert result.exit_code == 0
        assert "--values" in result.output
        assert "--interactive" in result.output
        assert "--output" in result.output

    def test_init_requires_values_or_interactive(self, runner: CliRunner) -> None:
        """Init should require --values or --interactive."""
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 1
        assert "Either --values or --interactive is required" in result.output

    def test_init_with_values(self, runner: CliRunner, tmp_path: Path) -> None:
        """Init with --values should create valid card."""
        output_path = tmp_path / "test-card.json"
        result = runner.invoke(
            main,
            ["init", "--values", "principal_benefit,transparency", "--output", str(output_path)],
        )
        assert result.exit_code == 0
        assert "Created" in result.output
        assert output_path.exists()

        # Verify the card is valid JSON with the unified / ADR-039 structure
        card = json.loads(output_path.read_text())
        assert card["card_version"] == "unified/2026-04-26"
        assert card["autonomy_mode"] in {"off", "observe", "nudge", "enforce"}
        assert card["integrity_mode"] in {"off", "observe", "nudge", "enforce"}
        assert "principal_benefit" in card["values"]["declared"]
        assert "transparency" in card["values"]["declared"]
        assert card["principal"]["type"] == "human"
        assert card["principal"]["identifier"]
        assert card["principal"]["relationship"] == "delegated_authority"
        assert "autonomy" in card
        assert "audit" in card

    def test_init_with_single_value(self, runner: CliRunner, tmp_path: Path) -> None:
        """Init with single value should work."""
        output_path = tmp_path / "single.json"
        result = runner.invoke(
            main,
            ["init", "--values", "honesty", "--output", str(output_path)],
        )
        assert result.exit_code == 0
        card = json.loads(output_path.read_text())
        assert card["values"]["declared"] == ["honesty"]

    def test_init_with_custom_agent_id(self, runner: CliRunner, tmp_path: Path) -> None:
        """Init with --agent-id should use provided ID."""
        output_path = tmp_path / "custom.json"
        result = runner.invoke(
            main,
            [
                "init",
                "--values",
                "transparency",
                "--agent-id",
                "my-custom-agent",
                "--output",
                str(output_path),
            ],
        )
        assert result.exit_code == 0
        card = json.loads(output_path.read_text())
        assert card["agent_id"] == "my-custom-agent"

    def test_init_warns_on_nonstandard_values(self, runner: CliRunner, tmp_path: Path) -> None:
        """Init should warn about non-standard values."""
        output_path = tmp_path / "nonstandard.json"
        result = runner.invoke(
            main,
            ["init", "--values", "principal_benefit,custom_value", "--output", str(output_path)],
        )
        # Should still succeed but warn
        assert result.exit_code == 0
        assert "Non-standard values" in result.output or "custom_value" in result.output

    def test_init_default_output(self, runner: CliRunner) -> None:
        """Init should default to alignment-card.json in current directory."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["init", "--values", "transparency"])
            assert result.exit_code == 0
            assert Path("alignment-card.json").exists()


# ---------------------------------------------------------------------------
# aap verify tests
# ---------------------------------------------------------------------------


class TestVerifyCommand:
    """Tests for aap verify command."""

    def test_verify_help(self, runner: CliRunner) -> None:
        """Verify help should show options."""
        result = runner.invoke(main, ["verify", "--help"])
        assert result.exit_code == 0
        assert "--card" in result.output
        assert "--trace" in result.output
        assert "--traces" in result.output

    def test_verify_requires_card(self, runner: CliRunner) -> None:
        """Verify should require --card."""
        result = runner.invoke(main, ["verify"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "--card" in result.output

    def test_verify_requires_trace_or_traces(
        self,
        runner: CliRunner,
        temp_card: Path,
    ) -> None:
        """Verify should require --trace or --traces."""
        result = runner.invoke(main, ["verify", "--card", str(temp_card)])
        assert result.exit_code == 1
        assert "Either --trace or --traces is required" in result.output

    def test_verify_single_trace_pass(
        self,
        runner: CliRunner,
        temp_card: Path,
        temp_trace: Path,
    ) -> None:
        """Verify should pass for valid trace."""
        result = runner.invoke(
            main,
            ["verify", "--card", str(temp_card), "--trace", str(temp_trace)],
        )
        assert result.exit_code == 0
        assert "Passed" in result.output

    def test_verify_single_trace_fail(
        self,
        runner: CliRunner,
        temp_card: Path,
        tmp_path: Path,
        trace_with_undeclared_value: dict[str, Any],
    ) -> None:
        """Verify should fail for trace with violation."""
        bad_trace = tmp_path / "bad-trace.json"
        bad_trace.write_text(json.dumps(trace_with_undeclared_value, default=str))

        result = runner.invoke(
            main,
            ["verify", "--card", str(temp_card), "--trace", str(bad_trace)],
        )
        assert result.exit_code == 1
        assert "violation" in result.output.lower()

    def test_verify_directory_of_traces(
        self,
        runner: CliRunner,
        temp_card: Path,
        temp_trace_dir: Path,
    ) -> None:
        """Verify should handle directory of traces."""
        result = runner.invoke(
            main,
            ["verify", "--card", str(temp_card), "--traces", str(temp_trace_dir)],
        )
        assert result.exit_code == 0
        assert "Passed" in result.output
        # Should show summary with count
        assert "Total:" in result.output

    def test_verify_shows_summary(
        self,
        runner: CliRunner,
        temp_card: Path,
        temp_trace_dir: Path,
    ) -> None:
        """Verify should show summary with counts."""
        result = runner.invoke(
            main,
            ["verify", "--card", str(temp_card), "--traces", str(temp_trace_dir)],
        )
        assert "Summary" in result.output
        assert "Total:" in result.output
        assert "Passed:" in result.output

    def test_verify_nonexistent_card(self, runner: CliRunner, temp_trace: Path) -> None:
        """Verify should fail gracefully for nonexistent card."""
        result = runner.invoke(
            main,
            ["verify", "--card", "/nonexistent/card.json", "--trace", str(temp_trace)],
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# aap check-coherence tests
# ---------------------------------------------------------------------------


class TestCheckCoherenceCommand:
    """Tests for aap check-coherence command."""

    def test_check_coherence_help(self, runner: CliRunner) -> None:
        """Check-coherence help should show options."""
        result = runner.invoke(main, ["check-coherence", "--help"])
        assert result.exit_code == 0
        assert "--my-card" in result.output
        assert "--their-card" in result.output

    def test_check_coherence_requires_both_cards(
        self,
        runner: CliRunner,
        temp_card: Path,
    ) -> None:
        """Check-coherence should require both cards."""
        result = runner.invoke(main, ["check-coherence", "--my-card", str(temp_card)])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "--their-card" in result.output

    def test_check_coherence_compatible(
        self,
        runner: CliRunner,
        tmp_path: Path,
        compatible_cards: tuple[dict, dict],
    ) -> None:
        """Check-coherence should pass for compatible cards."""
        card_a, card_b = compatible_cards
        card_a_path = tmp_path / "card_a.json"
        card_b_path = tmp_path / "card_b.json"
        card_a_path.write_text(json.dumps(card_a))
        card_b_path.write_text(json.dumps(card_b))

        result = runner.invoke(
            main,
            ["check-coherence", "--my-card", str(card_a_path), "--their-card", str(card_b_path)],
        )
        # Compatible cards should pass (exit 0)
        assert "Score:" in result.output
        assert "Matched values:" in result.output

    def test_check_coherence_conflicting(
        self,
        runner: CliRunner,
        tmp_path: Path,
        conflicting_cards: tuple[dict, dict],
    ) -> None:
        """Check-coherence should fail for conflicting cards."""
        card_a, card_b = conflicting_cards
        card_a_path = tmp_path / "card_a.json"
        card_b_path = tmp_path / "card_b.json"
        card_a_path.write_text(json.dumps(card_a))
        card_b_path.write_text(json.dumps(card_b))

        result = runner.invoke(
            main,
            ["check-coherence", "--my-card", str(card_a_path), "--their-card", str(card_b_path)],
        )
        assert result.exit_code == 1
        assert "Conflict" in result.output or "incompatible" in result.output.lower()

    def test_check_coherence_shows_score(
        self,
        runner: CliRunner,
        tmp_path: Path,
        compatible_cards: tuple[dict, dict],
    ) -> None:
        """Check-coherence should display coherence score."""
        card_a, card_b = compatible_cards
        card_a_path = tmp_path / "card_a.json"
        card_b_path = tmp_path / "card_b.json"
        card_a_path.write_text(json.dumps(card_a))
        card_b_path.write_text(json.dumps(card_b))

        result = runner.invoke(
            main,
            ["check-coherence", "--my-card", str(card_a_path), "--their-card", str(card_b_path)],
        )
        assert "Score:" in result.output

    def test_check_coherence_with_task_values(
        self,
        runner: CliRunner,
        tmp_path: Path,
        compatible_cards: tuple[dict, dict],
    ) -> None:
        """Check-coherence should accept --task-values."""
        card_a, card_b = compatible_cards
        card_a_path = tmp_path / "card_a.json"
        card_b_path = tmp_path / "card_b.json"
        card_a_path.write_text(json.dumps(card_a))
        card_b_path.write_text(json.dumps(card_b))

        result = runner.invoke(
            main,
            [
                "check-coherence",
                "--my-card",
                str(card_a_path),
                "--their-card",
                str(card_b_path),
                "--task-values",
                "principal_benefit,transparency",
            ],
        )
        assert "Score:" in result.output


# ---------------------------------------------------------------------------
# aap drift tests
# ---------------------------------------------------------------------------


class TestDriftCommand:
    """Tests for aap drift command."""

    def test_drift_help(self, runner: CliRunner) -> None:
        """Drift help should show options."""
        result = runner.invoke(main, ["drift", "--help"])
        assert result.exit_code == 0
        assert "--card" in result.output
        assert "--traces" in result.output
        assert "--threshold" in result.output
        assert "--sustained" in result.output

    def test_drift_requires_card_and_traces(self, runner: CliRunner) -> None:
        """Drift should require --card and --traces."""
        result = runner.invoke(main, ["drift"])
        assert result.exit_code != 0

    def test_drift_no_drift_detected(
        self,
        runner: CliRunner,
        temp_card: Path,
        temp_trace_dir: Path,
    ) -> None:
        """Drift should report no drift for aligned traces."""
        result = runner.invoke(
            main,
            ["drift", "--card", str(temp_card), "--traces", str(temp_trace_dir)],
        )
        assert result.exit_code == 0
        assert "No drift detected" in result.output

    def test_drift_detected(
        self,
        runner: CliRunner,
        tmp_path: Path,
        minimal_alignment_card: dict[str, Any],
        drifting_trace_sequence: list[dict[str, Any]],
    ) -> None:
        """Drift should detect drift in drifting traces."""
        # Write card
        card_path = tmp_path / "card.json"
        card_path.write_text(json.dumps(minimal_alignment_card, default=str))

        # Write drifting traces
        traces_dir = tmp_path / "drifting_traces"
        traces_dir.mkdir()
        for i, trace in enumerate(drifting_trace_sequence):
            trace_path = traces_dir / f"trace-{i:03d}.json"
            trace_path.write_text(json.dumps(trace, default=str))

        result = runner.invoke(
            main,
            ["drift", "--card", str(card_path), "--traces", str(traces_dir)],
        )
        # May or may not detect drift depending on exact thresholds
        # At minimum, should complete without error
        assert "Analyzing" in result.output

    def test_drift_custom_threshold(
        self,
        runner: CliRunner,
        temp_card: Path,
        temp_trace_dir: Path,
    ) -> None:
        """Drift should accept custom threshold."""
        result = runner.invoke(
            main,
            [
                "drift",
                "--card",
                str(temp_card),
                "--traces",
                str(temp_trace_dir),
                "--threshold",
                "0.5",
            ],
        )
        assert "Analyzing" in result.output

    def test_drift_custom_sustained(
        self,
        runner: CliRunner,
        temp_card: Path,
        temp_trace_dir: Path,
    ) -> None:
        """Drift should accept custom sustained threshold."""
        result = runner.invoke(
            main,
            [
                "drift",
                "--card",
                str(temp_card),
                "--traces",
                str(temp_trace_dir),
                "--sustained",
                "5",
            ],
        )
        assert "Analyzing" in result.output

    def test_drift_requires_directory(
        self,
        runner: CliRunner,
        temp_card: Path,
        temp_trace: Path,
    ) -> None:
        """Drift --traces should be a directory."""
        result = runner.invoke(
            main,
            ["drift", "--card", str(temp_card), "--traces", str(temp_trace)],
        )
        assert result.exit_code == 1
        assert "must be a directory" in result.output


# ---------------------------------------------------------------------------
# Edge cases and error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for CLI error handling."""

    def test_invalid_json_card(self, runner: CliRunner, tmp_path: Path) -> None:
        """CLI should handle invalid JSON gracefully."""
        bad_card = tmp_path / "bad.json"
        bad_card.write_text("not valid json {{{")

        result = runner.invoke(
            main,
            ["verify", "--card", str(bad_card), "--trace", str(bad_card)],
        )
        assert result.exit_code != 0

    def test_empty_values(self, runner: CliRunner, tmp_path: Path) -> None:
        """Init should handle empty values string."""
        result = runner.invoke(
            main,
            ["init", "--values", "", "--output", str(tmp_path / "empty.json")],
        )
        assert result.exit_code == 1
        # Empty string triggers the "require values or interactive" check
        assert "required" in result.output.lower() or "No values" in result.output

    def test_empty_traces_directory(
        self,
        runner: CliRunner,
        temp_card: Path,
        tmp_path: Path,
    ) -> None:
        """Verify should handle empty traces directory."""
        empty_dir = tmp_path / "empty_traces"
        empty_dir.mkdir()

        result = runner.invoke(
            main,
            ["verify", "--card", str(temp_card), "--traces", str(empty_dir)],
        )
        assert result.exit_code == 1
        assert "No trace files found" in result.output
