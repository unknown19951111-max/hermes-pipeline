"""
Job state management — persistent state, artifact storage, checkpointing.
"""

import hashlib
import json
import os
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class ArtifactStore:
    """Persistent storage for pipeline artifacts with provenance tracking."""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.artifacts_dir = self.base_dir / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def store_finding(self, job_id: str, finding: dict) -> str:
        """Store a normalized finding record. Returns the file path."""
        job_dir = self.artifacts_dir / job_id / "findings"
        job_dir.mkdir(parents=True, exist_ok=True)
        
        finding_id = finding.get("finding_id", str(uuid.uuid4()))
        file_path = job_dir / f"{finding_id}.json"
        file_path.write_text(json.dumps(finding, indent=2, default=str))
        return str(file_path)

    def store_manifest(self, job_id: str, manifest: dict, name: str = "intake") -> str:
        """Store an execution or intake manifest."""
        job_dir = self.artifacts_dir / job_id / "manifests"
        job_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = job_dir / f"{name}.json"
        file_path.write_text(json.dumps(manifest, indent=2, default=str))
        return str(file_path)

    def store_raw_output(self, job_id: str, stage_id: str, content: str,
                         suffix: str = "txt") -> str:
        """Store raw tool output."""
        job_dir = self.artifacts_dir / job_id / "raw" / stage_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = job_dir / f"output.{suffix}"
        file_path.write_text(content)
        return str(file_path)

    def store_build_log(self, job_id: str, log: str) -> str:
        """Store build log."""
        job_dir = self.artifacts_dir / job_id / "build"
        job_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = job_dir / "build.log"
        file_path.write_text(log)
        return str(file_path)

    def store_corpus(self, job_id: str, corpus_dir: str) -> Optional[str]:
        """Archive a corpus directory. Returns archive path."""
        if not Path(corpus_dir).exists():
            return None
        
        job_dir = self.artifacts_dir / job_id / "corpora"
        job_dir.mkdir(parents=True, exist_ok=True)
        
        archive_path = job_dir / f"corpus-{int(time.time())}.tar.gz"
        shutil.make_archive(
            str(archive_path).replace(".tar.gz", ""),
            "gztar",
            corpus_dir,
        )
        return str(archive_path)

    def generate_report(self, job_id: str, findings: list[dict],
                        intake_manifest: dict, stage_results: list[dict]) -> dict:
        """Generate the final pipeline report."""
        # Separate findings by classification
        by_class = {
            "confirmed_vulnerabilities": [],
            "reproducible_suspicious": [],
            "invariant_violations": [],
            "tool_warnings": [],
            "informational": [],
            "unsupported_hypotheses": [],
            "false_positives": [],
            "duplicate_groups": [],
            "analysis_failures": [],
        }
        
        for f in findings:
            cls = f.get("classification", "")
            if cls == "confirmed_vulnerability":
                by_class["confirmed_vulnerabilities"].append(f)
            elif cls == "reproducible_suspicious_behavior":
                by_class["reproducible_suspicious"].append(f)
            elif cls == "invariant_violation":
                by_class["invariant_violations"].append(f)
            elif cls == "tool_generated_warning":
                by_class["tool_warnings"].append(f)
            elif cls == "informational_observation":
                by_class["informational"].append(f)
            elif cls == "unsupported_hypothesis":
                by_class["unsupported_hypotheses"].append(f)
            elif cls == "false_positive":
                by_class["false_positives"].append(f)
            elif cls == "duplicate_finding":
                by_class["duplicate_groups"].append(f)
            elif cls == "analysis_failure":
                by_class["analysis_failures"].append(f)
        
        # Collect stage info
        stages = {
            "completed": [s.get("stage_id") for s in stage_results if s.get("completion_state") == "completed"],
            "failed": [s.get("stage_id") for s in stage_results if s.get("completion_state") == "failed"],
            "timed_out": [s.get("stage_id") for s in stage_results if s.get("completion_state") == "timed_out"],
            "skipped": [s.get("stage_id") for s in stage_results if s.get("completion_state") == "skipped"],
        }
        
        report = {
            "job_id": job_id,
            "target": {
                "url": intake_manifest.get("target", {}).get("url", ""),
                "commit": intake_manifest.get("commit_sha", ""),
                "ecosystem": intake_manifest.get("ecosystem", ""),
                "framework": intake_manifest.get("framework", ""),
                "compiler_version": "",
            },
            "findings": by_class,
            "stages": stages,
            "coverage": {
                "tools_run": list(set(s.get("tool", "") for s in stage_results if s.get("completion_state") == "completed")),
                "tools_failed": list(set(s.get("tool", "") for s in stage_results if s.get("completion_state") == "failed")),
                "tools_skipped": list(set(s.get("tool", "") for s in stage_results if s.get("completion_state") == "skipped")),
                "unreached_stages": [],
                "notes": [],
            },
            "provenance": {
                "pipeline_version": "0.1.0",
                "schema_version": "1.0.0",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": self._compute_duration(stage_results),
            },
            "schema_version": "1.0.0",
        }

        return report

    def _compute_duration(self, stage_results: list[dict]) -> float:
        """Compute pipeline duration from stage result timestamps."""
        start_times = []
        end_times = []
        for s in stage_results:
            st = s.get("start_time", "")
            et = s.get("end_time", "")
            if st:
                try:
                    start_times.append(datetime.fromisoformat(st).timestamp())
                except (ValueError, TypeError):
                    pass
            if et:
                try:
                    end_times.append(datetime.fromisoformat(et).timestamp())
                except (ValueError, TypeError):
                    pass
        if start_times and end_times:
            return max(end_times) - min(start_times)
        return 0.0

    def store_report(self, job_id: str, report: dict) -> str:
        """Store the final report."""
        job_dir = self.artifacts_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = job_dir / "report.json"
        file_path.write_text(json.dumps(report, indent=2, default=str))
        return str(file_path)


class JobState:
    """Persistent job state machine."""

    STATES = ["queued", "running", "completed", "failed", "timed_out",
              "skipped", "cancelled", "blocked", "awaiting_human_review"]

    def __init__(self, state_dir: str):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def create(self, job_id: str, manifest: dict) -> dict:
        """Create a new job state record."""
        state = {
            "job_id": job_id,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "manifest": manifest,
            "stage_results": [],
            "findings": [],
            "checkpoints": {},
            "errors": [],
            "retry_count": 0,
        }
        self._save(job_id, state)
        return state

    def transition(self, job_id: str, new_status: str) -> dict:
        """Transition job to a new state."""
        if new_status not in self.STATES:
            raise ValueError(f"Invalid state: {new_status}")
        
        state = self._load(job_id)
        state["status"] = new_status
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save(job_id, state)
        return state

    def add_stage_result(self, job_id: str, result: dict) -> dict:
        """Record a stage execution result."""
        state = self._load(job_id)
        state["stage_results"].append(result)
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save(job_id, state)
        return state

    def add_finding(self, job_id: str, finding: dict) -> dict:
        """Record a finding (stores reference, not full content)."""
        state = self._load(job_id)
        state["findings"].append({
            "finding_id": finding.get("finding_id"),
            "classification": finding.get("classification"),
            "severity": finding.get("severity"),
            "tool": finding.get("tool", {}).get("name"),
            "title": finding.get("title", ""),
        })
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save(job_id, state)
        return state

    def save_checkpoint(self, job_id: str, stage_id: str, data: dict) -> dict:
        """Save a checkpoint for resumable jobs."""
        state = self._load(job_id)
        state["checkpoints"][stage_id] = {
            "data": data,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save(job_id, state)
        return state

    def get_checkpoint(self, job_id: str, stage_id: str) -> Optional[dict]:
        """Get a saved checkpoint."""
        state = self._load(job_id)
        cp = state.get("checkpoints", {}).get(stage_id)
        return cp.get("data") if cp else None

    def get(self, job_id: str) -> dict:
        """Get current job state."""
        return self._load(job_id)

    def list_jobs(self, status: Optional[str] = None) -> list[dict]:
        """List all jobs, optionally filtered by status."""
        jobs = []
        for f in self.state_dir.glob("*.json"):
            try:
                state = json.loads(f.read_text())
                if status is None or state.get("status") == status:
                    jobs.append(state)
            except Exception:
                continue
        return sorted(jobs, key=lambda j: j.get("created_at", ""), reverse=True)

    def _save(self, job_id: str, state: dict):
        """Atomically save job state."""
        file_path = self.state_dir / f"{job_id}.json"
        tmp_path = file_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(state, indent=2, default=str))
        tmp_path.rename(file_path)

    def _load(self, job_id: str) -> dict:
        """Load job state from disk."""
        file_path = self.state_dir / f"{job_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Job {job_id} not found")
        return json.loads(file_path.read_text())

    def cleanup(self, job_id: str):
        """Remove a job's state."""
        file_path = self.state_dir / f"{job_id}.json"
        if file_path.exists():
            file_path.unlink()