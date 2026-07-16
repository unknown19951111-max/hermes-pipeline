"""
Intake subsystem — accepts remote or local targets, pins commit, produces intake manifest.

This module handles:
- Repository cloning and commit pinning
- Local path intake
- Scope-file parsing
- Target validation
- Intake manifest generation (immutable snapshot)
"""

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class IntakeError(Exception):
    """Base exception for intake failures."""
    pass


class SymlinkIntakeError(IntakeError):
    """Raised when symlinks are detected in the source tree."""
    pass


class IntakeManifest:
    """Immutable intake manifest for a pipeline job."""

    SCHEMA_VERSION = "1.0.0"

    def __init__(self, data: dict):
        self.data = data
        self._validate()

    def _validate(self):
        required = ["job_id", "target", "commit_sha", "ecosystem",
                     "framework", "intake_timestamp", "verification_state"]
        for field in required:
            if field not in self.data:
                raise IntakeError(f"Missing required field: {field}")

    def to_dict(self) -> dict:
        return dict(self.data)

    def to_json(self) -> str:
        return json.dumps(self.data, indent=2, default=str)

    @classmethod
    def create(cls, job_id: str, target_type: str, commit_sha: str,
               ecosystem: str = "unknown", framework: str = "unknown",
               **kwargs) -> "IntakeManifest":
        data = {
            "job_id": job_id,
            "target": {
                "type": target_type,
                **kwargs
            },
            "commit_sha": commit_sha,
            "ecosystem": ecosystem,
            "framework": framework,
            "framework_confidence": kwargs.get("framework_confidence", 0.0),
            "intake_timestamp": datetime.now(timezone.utc).isoformat(),
            "verification_state": "pending",
            "dependency_state": "unknown",
            "submodule_state": "unknown",
            "program_eligibility_ref": kwargs.get("program_eligibility_ref", ""),
            "input_hashes": kwargs.get("input_hashes", {}),
            "size_bytes": kwargs.get("size_bytes", 0),
            "errors": kwargs.get("errors", []),
            "schema_version": cls.SCHEMA_VERSION,
        }
        return cls(data)


class RepositoryManager:
    """Manages repository intake — clone, pin, validate."""

    MAX_CLONE_SIZE_MB = 500
    CLONE_TIMEOUT_S = 120

    def __init__(self, work_dir: str):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def intake_remote(self, url: str, branch: Optional[str] = None,
                      commit: Optional[str] = None) -> tuple[str, str, dict]:
        """
        Clone a remote repository and pin a commit.
        
        Returns: (job_id, workspace_path, manifest_dict)
        """
        job_id = str(uuid.uuid4())
        workspace = self.work_dir / job_id
        workspace.mkdir(parents=True, exist_ok=True)

        try:
            # Clone repository
            clone_cmd = ["git", "clone", "--depth", "1"]
            if branch:
                clone_cmd.extend(["--branch", branch])
            clone_cmd.extend([url, str(workspace / "repo")])

            result = subprocess.run(
                clone_cmd,
                capture_output=True,
                text=True,
                timeout=self.CLONE_TIMEOUT_S,
            )

            if result.returncode != 0:
                shutil.rmtree(workspace, ignore_errors=True)
                raise IntakeError(f"Clone failed: {result.stderr.strip()}")

            repo_path = workspace / "repo"

            # Get pinned commit SHA
            if commit:
                # Checkout specific commit
                subprocess.run(
                    ["git", "checkout", commit],
                    cwd=repo_path,
                    capture_output=True,
                    timeout=30,
                )

            # Get actual commit SHA
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            commit_sha = result.stdout.strip()

            # Calculate size
            size_bytes = sum(
                f.stat().st_size for f in repo_path.rglob("*") if f.is_file()
            )

            # Create manifest — derive owner/name from URL
            url_clean = url.rstrip("/").replace(".git", "")
            url_parts = url_clean.split("/")
            owner = url_parts[-2] if len(url_parts) >= 2 else ""
            name = url_parts[-1] if len(url_parts) >= 1 else ""

            manifest = IntakeManifest.create(
                job_id=job_id,
                target_type="remote",
                url=url,
                branch=branch or "",
                owner=owner,
                name=name,
                commit_sha=commit_sha,
                size_bytes=size_bytes,
            )

            return job_id, str(repo_path), manifest.to_dict()

        except subprocess.TimeoutExpired:
            shutil.rmtree(workspace, ignore_errors=True)
            raise IntakeError(f"Clone timed out after {self.CLONE_TIMEOUT_S}s")
        except Exception as e:
            shutil.rmtree(workspace, ignore_errors=True)
            raise IntakeError(f"Intake failed: {e}")

    def intake_local(self, local_path: str) -> tuple[str, str, dict]:
        """
        Intake a local project directory.

        Returns: (job_id, workspace_path, manifest_dict)
        """
        path = Path(local_path).resolve()
        if not path.exists():
            raise IntakeError(f"Local path does not exist: {local_path}")
        if not path.is_dir():
            raise IntakeError(f"Local path is not a directory: {local_path}")

        job_id = str(uuid.uuid4())
        workspace = self.work_dir / job_id
        workspace.mkdir(parents=True, exist_ok=True)

        try:
            # SECURITY: Reject all symlinks before copying
            resolved_source = path.resolve()
            for entry in resolved_source.rglob("*"):
                if entry.is_symlink():
                    raise SymlinkIntakeError(
                        f"Symlink detected at {entry.name} — target {entry.resolve()}. "
                        f"Symlinks are not allowed in local intake."
                    )

            # Copy local project to workspace (safe copy)
            dest_path = workspace / "repo"
            shutil.copytree(str(path), str(dest_path), symlinks=False,
                            ignore=shutil.ignore_patterns(
                                ".git", "node_modules", "cache", ".cache",
                                "target", "out", ".venv", "venv"
                            ))

            # Try to get commit from original repo
            commit_sha = "unknown"
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    commit_sha = result.stdout.strip()
            except Exception:
                pass

            # Calculate size
            size_bytes = sum(
                f.stat().st_size for f in dest_path.rglob("*") if f.is_file()
            )

            manifest = IntakeManifest.create(
                job_id=job_id,
                target_type="local",
                local_path=str(path),
                commit_sha=commit_sha,
                size_bytes=size_bytes,
            )

            return job_id, str(dest_path), manifest.to_dict()

        except Exception as e:
            shutil.rmtree(workspace, ignore_errors=True)
            raise IntakeError(f"Local intake failed: {e}")

    @staticmethod
    def validate_workspace(workspace: str) -> bool:
        """Validate that a workspace directory is safe."""
        path = Path(workspace)
        if not path.exists() or not path.is_dir():
            return False

        # Check for symlinks — reject all
        for f in path.rglob("*"):
            if f.is_symlink():
                return False

        return True
