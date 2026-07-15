"""
Failure isolation — circuit breakers, tool failure isolation, partial-result survival, checkpoint resumption.
"""

import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class CircuitBreaker:
    """
    Per-tool circuit breaker: N consecutive failures → trip → route around.
    
    Once tripped, the tool is disabled for the current run and its stage
    is marked NOT SUPPORTED rather than FAILED. This means the pipeline
    continues without that tool instead of aborting.
    """

    def __init__(self, threshold: int = 3, reset_after_s: int = 300):
        self.threshold = threshold
        self.reset_after_s = reset_after_s
        self._failures: dict[str, list[float]] = defaultdict(list)
        self._tripped: dict[str, bool] = {}

    def record_failure(self, tool_name: str):
        """Record a tool failure and check if circuit should trip."""
        now = time.time()
        self._failures[tool_name].append(now)

        # Prune old failures outside the reset window
        self._failures[tool_name] = [
            t for t in self._failures[tool_name]
            if now - t < self.reset_after_s
        ]

        # Check threshold
        if len(self._failures[tool_name]) >= self.threshold:
            self._tripped[tool_name] = True
            return True  # Circuit tripped

        return False

    def is_tripped(self, tool_name: str) -> bool:
        """Check if a tool's circuit breaker is tripped."""
        return self._tripped.get(tool_name, False)

    def reset(self, tool_name: str):
        """Manually reset a circuit breaker."""
        self._failures[tool_name] = []
        self._tripped[tool_name] = False

    def state(self) -> dict:
        """Get circuit breaker state for all tools."""
        return {
            tool: {
                "tripped": tripped,
                "recent_failures": len(self._failures.get(tool, [])),
                "threshold": self.threshold,
            }
            for tool, tripped in self._tripped.items()
        }


class FailureHandler:
    """
    Central failure handler: determines root cause, classifies errors,
    preserves partial results, and manages retry logic.
    """

    RETRY_POLICIES = {
        "transient": {"max_retries": 3, "backoff_s": 5, "backoff_multiplier": 2},
        "timeout": {"max_retries": 1, "backoff_s": 10, "backoff_multiplier": 2},
        "oom": {"max_retries": 0, "backoff_s": 0, "backoff_multiplier": 1},
        "deterministic": {"max_retries": 0, "backoff_s": 0, "backoff_multiplier": 1},
        "unsupported": {"max_retries": 0, "backoff_s": 0, "backoff_multiplier": 1},
        "unknown": {"max_retries": 1, "backoff_s": 5, "backoff_multiplier": 1},
    }

    def __init__(self, artifact_store=None, circuit_breaker: CircuitBreaker = None):
        self.artifact_store = artifact_store
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self._retries: dict[str, int] = {}

    def classify_error(self, exit_code: int, timed_out: bool,
                       stderr: str, stdout: str) -> str:
        """Classify an error into a root-cause category."""
        if timed_out:
            return "timeout"
        if exit_code == -9 or "killed" in (stderr or "").lower():
            return "oom"
        if exit_code == -1 or exit_code == 255:
            if not stderr and stdout:
                return "unknown"  # Tool ran but returned odd code
            return "transient"
        if "not found" in (stderr or "").lower():
            return "unsupported"
        if exit_code != 0:
            # Non-zero but has output
            if stdout and len(stdout) > 100:
                return "transient"  # Partial output available
            return "deterministic"
        return "unknown"

    def should_retry(self, tool_name: str, error_class: str,
                     current_retry: int) -> bool:
        """Determine if a retry should be attempted."""
        policy = self.RETRY_POLICIES.get(error_class, self.RETRY_POLICIES["unknown"])
        return current_retry < policy["max_retries"]

    def get_backoff(self, error_class: str, current_retry: int) -> float:
        """Get backoff duration for a retry."""
        policy = self.RETRY_POLICIES.get(error_class, self.RETRY_POLICIES["unknown"])
        return policy["backoff_s"] * (policy["backoff_multiplier"] ** current_retry)

    def handle_tool_failure(self, tool_name: str, stage_id: str,
                             exit_code: int, timed_out: bool,
                             stderr: str, stdout: str,
                             job_state, job_id: str,
                             partial_findings: list[dict] = None) -> dict:
        """
        Handle a tool failure: classify, circuit break, preserve partial results.
        
        Returns: result_dict with completion_state and findings.
        """
        error_class = self.classify_error(exit_code, timed_out, stderr, stdout)
        retry_count = self._retries.get(f"{job_id}:{tool_name}", 0)

        # Check circuit breaker
        if self.circuit_breaker.is_tripped(tool_name):
            return {
                "stage_id": stage_id,
                "tool": tool_name,
                "completion_state": "skipped",
                "completion_state_reason": f"Circuit breaker tripped for {tool_name}",
                "error_classification": error_class,
                "retries_exhausted": True,
                "partial_findings": partial_findings or [],
            }

        # Preserve partial findings
        if partial_findings and self.artifact_store:
            for finding in partial_findings:
                self.artifact_store.store_finding(job_id, finding)

        # Determine completion state
        if exit_code == -9:
            completion_state = "failed"
        elif timed_out:
            if partial_findings:
                completion_state = "partial"
            else:
                completion_state = "timed_out"
        elif exit_code == -1:
            completion_state = "failed" if not partial_findings else "partial"
        else:
            completion_state = "failed"

        # Record for circuit breaker
        if not self.should_retry(tool_name, error_class, retry_count):
            self.circuit_breaker.record_failure(tool_name)

        # Record retry
        self._retries[f"{job_id}:{tool_name}"] = retry_count + 1

        return {
            "stage_id": stage_id,
            "tool": tool_name,
            "completion_state": completion_state,
            "completion_state_reason": f"{error_class} error, exit={exit_code}, "
                                       f"timed_out={timed_out}, retry={retry_count}",
            "error_classification": error_class,
            "retries_exhausted": not self.should_retry(tool_name, error_class, retry_count),
            "partial_findings": partial_findings or [],
        }


class CheckpointManager:
    """
    Manages job checkpoints for resumable pipeline execution.
    
    Each checkpoint records:
    - The stage that completed
    - Corpus directory path (for fuzzer stages)
    - Any intermediate results
    - Timestamp
    
    A killed job can be resumed from its last checkpoint, skipping completed stages.
    """

    def __init__(self, state_dir: str):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(self, job_id: str, stage_id: str,
                         data: dict) -> dict:
        """Save a checkpoint for a job stage."""
        checkpoint = {
            "job_id": job_id,
            "stage_id": stage_id,
            "data": data,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        path = self.state_dir / f"{job_id}__{stage_id}.checkpoint"
        path.write_text(json.dumps(checkpoint, indent=2))
        return checkpoint

    def load_checkpoint(self, job_id: str, stage_id: str) -> Optional[dict]:
        """Load a checkpoint for a job stage."""
        path = self.state_dir / f"{job_id}__{stage_id}.checkpoint"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def list_checkpoints(self, job_id: str) -> list[str]:
        """List all checkpoint stage IDs for a job."""
        checkpoints = []
        for f in self.state_dir.glob(f"{job_id}__*.checkpoint"):
            stage = f.stem.replace(f"{job_id}__", "")
            checkpoints.append(stage)
        return sorted(checkpoints)

    def has_checkpoint(self, job_id: str, stage_id: str) -> bool:
        """Check if a checkpoint exists for a stage."""
        return (self.state_dir / f"{job_id}__{stage_id}.checkpoint").exists()

    def get_earliest_uncompleted_stage(self, job_id: str,
                                        stages: list[str]) -> Optional[str]:
        """Find the first stage that doesn't have a checkpoint."""
        for stage in stages:
            if not self.has_checkpoint(job_id, stage):
                return stage
        return None

    def delete_checkpoint(self, job_id: str, stage_id: str):
        """Delete a checkpoint."""
        path = self.state_dir / f"{job_id}__{stage_id}.checkpoint"
        if path.exists():
            path.unlink()

    def get_all_checkpoints(self) -> list[dict]:
        """Get all checkpoints across all jobs."""
        checkpoints = []
        for f in self.state_dir.glob("*.checkpoint"):
            try:
                checkpoints.append(json.loads(f.read_text()))
            except Exception:
                continue
        return checkpoints