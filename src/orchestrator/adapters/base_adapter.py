"""
Base adapter class for all pipeline tool adapters.
"""

import json
import os
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class AdapterResult:
    """Standard result from any tool adapter."""
    success: bool
    tool: str
    tool_version: str
    adapter_version: str
    command: str
    exit_code: int
    timed_out: bool
    stdout: str
    stderr: str
    raw_output_paths: list[str]
    normalized_findings: list[dict] = field(default_factory=list)
    execution_manifest: dict = field(default_factory=dict)
    coverage_limitations: list[str] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0
    error: Optional[str] = None

    def to_manifest(self, job_id: str, stage_id: str, work_dir: str) -> dict:
        return {
            "job_id": job_id,
            "stage_id": stage_id,
            "tool": self.tool,
            "tool_version": self.tool_version,
            "adapter_version": self.adapter_version,
            "schema_version": "1.0.0",
            "command": self.command,
            "arguments": [],
            "working_directory": work_dir,
            "environment_allowlist": [],
            "start_time": self.start_time or datetime.now(timezone.utc).isoformat(),
            "end_time": self.end_time or datetime.now(timezone.utc).isoformat(),
            "duration_seconds": self.duration_seconds,
            "exit_code": self.exit_code,
            "timeout": self.timed_out,
            "resources": {},
            "output_hashes": {},
            "artifact_paths": self.raw_output_paths,
            "target_commit": "",
            "compiler_version": "",
            "container_image_digest": "",
            "fork_chain": "",
            "fork_block": 0,
            "retry_count": 0,
            "error_classification": (
                "timeout" if self.timed_out
                else "deterministic" if self.exit_code != 0
                else "unknown"
            ),
            "completion_state": (
                "completed" if self.success
                else "timed_out" if self.timed_out
                else "failed"
            ),
            "coverage_limitations": self.coverage_limitations,
        }


class ToolAdapter(ABC):
    """Base class for all tool adapters."""

    ADAPTER_VERSION = "0.1.0"

    def __init__(self, work_dir: str):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def check_dependencies(self) -> bool:
        """Check if the tool binary is available."""
        pass

    @abstractmethod
    def get_version(self) -> str:
        """Get the installed tool version."""
        pass

    @abstractmethod
    def build_command(self, target_dir: str, **kwargs) -> list[str]:
        """Build the command to run the tool."""
        pass

    @abstractmethod
    def parse_output(self, stdout: str, stderr: str, output_paths: list[str]) -> list[dict]:
        """Parse raw output into normalized findings."""
        pass

    def run(self, target_dir: str, job_id: str, timeout_s: int = 120,
            **kwargs) -> AdapterResult:
        """Run the tool adapter — dependency check, execution, parsing."""
        # Check dependencies
        if not self.check_dependencies():
            return AdapterResult(
                success=False, tool=self.__class__.__name__,
                tool_version="", adapter_version=self.ADAPTER_VERSION,
                command="", exit_code=-1, timed_out=False,
                stdout="", stderr="", raw_output_paths=[],
                error=f"Tool {self.__class__.__name__} not found in PATH",
            )

        tool_version = self.get_version()

        # Build and execute command
        cmd = self.build_command(target_dir, **kwargs)
        cmd_str = " ".join(str(c) for c in cmd)

        _start = time.time()
        try:
            result = subprocess.run(
                cmd, cwd=target_dir,
                capture_output=True, text=True,
                timeout=timeout_s,
            )
            timed_out = False
            stdout = result.stdout
            stderr = result.stderr
            exit_code = result.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            stdout = ""
            stderr = f"TIMEOUT after {timeout_s}s"
            exit_code = -1

        _end = time.time()

        # Save raw output
        output_paths = []
        if stdout:
            out_path = str(self.work_dir / f"{job_id}_stdout.txt")
            Path(out_path).write_text(stdout)
            output_paths.append(out_path)
        if stderr:
            err_path = str(self.work_dir / f"{job_id}_stderr.txt")
            Path(err_path).write_text(stderr)
            output_paths.append(err_path)

        # Parse output
        normalized = []
        if stdout:
            try:
                normalized = self.parse_output(stdout, stderr, output_paths)
            except Exception as e:
                # Malformed output → quarantine, don't crash
                normalized = [{
                    "finding_id": f"{job_id}-parse-error",
                    "classification": "analysis_failure",
                    "tool": {"name": self.__class__.__name__, "version": tool_version, "rule_id": "parse-error"},
                    "title": f"Failed to parse {self.__class__.__name__} output",
                    "description": str(e),
                    "raw_output_saved": output_paths[-1] if output_paths else "",
                }]

        # Determine success — partial results still produce findings
        success = exit_code == 0 or len(normalized) > 0

        return AdapterResult(
            success=success,
            tool=self.__class__.__name__,
            tool_version=tool_version,
            adapter_version=self.ADAPTER_VERSION,
            command=cmd_str,
            exit_code=exit_code,
            timed_out=timed_out,
            stdout=stdout,
            stderr=stderr,
            raw_output_paths=output_paths,
            normalized_findings=normalized,
            error=None if success else stderr[:500] if stderr else "Unknown error",
            start_time=datetime.fromtimestamp(_start, tz=timezone.utc).isoformat(),
            end_time=datetime.fromtimestamp(_end, tz=timezone.utc).isoformat(),
            duration_seconds=_end - _start,
        )