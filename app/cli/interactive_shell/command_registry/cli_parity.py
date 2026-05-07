"""Slash commands for CLI parity, delegating to the Click CLI via subprocess."""

from __future__ import annotations

import subprocess
import sys

from rich.console import Console

from app.cli.interactive_shell.command_registry.types import ExecutionTier, SlashCommand
from app.cli.interactive_shell.session import ReplSession


def run_cli_command(console: Console, args: list[str]) -> bool:
    """Helper to delegate complex or interactive Click commands to a child process.

    NOTE: This call is synchronous and blocking. This is intentional to support
    interactive CLI workflows (wizards, pickers) that require standard input.
    Users can interrupt a hanging or slow command using Ctrl+C.
    """
    console.print()
    cmd = [sys.executable, "-m", "app.cli", *args]
    try:
        # 5-minute timeout as a safety guard for network-touching commands (like /update).
        # Interactive wizards will still work as long as the user provides input
        # and the process finishes within this window.
        result = subprocess.run(cmd, check=False, timeout=300)
        if result.returncode != 0:
            console.print(
                f"[red]CLI command exited with non-zero code {result.returncode}[/red]"
            )
    except subprocess.TimeoutExpired:
        console.print("[red]error:[/red] CLI command timed out after 5 minutes")
    except Exception as exc:
        console.print(f"[red]error running CLI command:[/red] {exc}")
    console.print()
    return True



def _cmd_onboard(session: ReplSession, console: Console, args: list[str]) -> bool:  # noqa: ARG001
    return run_cli_command(console, ["onboard", *args])


def _cmd_deploy(session: ReplSession, console: Console, args: list[str]) -> bool:  # noqa: ARG001
    return run_cli_command(console, ["deploy", *args])


def _cmd_remote(session: ReplSession, console: Console, args: list[str]) -> bool:  # noqa: ARG001
    return run_cli_command(console, ["remote", *args])


def _cmd_tests(session: ReplSession, console: Console, args: list[str]) -> bool:  # noqa: ARG001
    return run_cli_command(console, ["tests", *args])


def _cmd_guardrails(session: ReplSession, console: Console, args: list[str]) -> bool:  # noqa: ARG001
    return run_cli_command(console, ["guardrails", *args])


def _cmd_update(session: ReplSession, console: Console, args: list[str]) -> bool:  # noqa: ARG001
    return run_cli_command(console, ["update", *args])


def _cmd_uninstall(session: ReplSession, console: Console, args: list[str]) -> bool:  # noqa: ARG001
    return run_cli_command(console, ["uninstall", *args])


COMMANDS: list[SlashCommand] = [
    SlashCommand(
        "/onboard",
        "run the interactive onboarding wizard ('/onboard local_llm')",
        _cmd_onboard,
        execution_tier=ExecutionTier.SAFE,
    ),
    SlashCommand(
        "/deploy",
        "deploy OpenSRE to a cloud environment ('/deploy ec2|langsmith|railway')",
        _cmd_deploy,
        execution_tier=ExecutionTier.SAFE,
    ),
    SlashCommand(
        "/remote",
        "connect to and trigger a remote deployed agent ('/remote health|investigate|ops|pull|trigger')",
        _cmd_remote,
        execution_tier=ExecutionTier.SAFE,
    ),
    SlashCommand(
        "/tests",
        "browse and run inventoried tests ('/tests list|run|synthetic')",
        _cmd_tests,
        execution_tier=ExecutionTier.SAFE,
    ),
    SlashCommand(
        "/guardrails",
        "manage sensitive information guardrail rules ('/guardrails audit|init|rules|test')",
        _cmd_guardrails,
        execution_tier=ExecutionTier.SAFE,
    ),
    SlashCommand(
        "/update",
        "check for a newer version and update if available",
        _cmd_update,
        execution_tier=ExecutionTier.SAFE,
    ),
    SlashCommand(
        "/uninstall",
        "remove opensre and all local data from this machine",
        _cmd_uninstall,
        execution_tier=ExecutionTier.ELEVATED,
    ),
]
