"""
Medusa adapter — runs Medusa parallel coverage-guided fuzzer and preserves corpus.
"""

import json
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Optional

from ..adapters.base_adapter import ToolAdapter, AdapterResult


class MedusaAdapter(ToolAdapter):
    """Adapter for running Medusa fuzzing, preserving corpus and failing sequences."""

    ADAPTER_VERSION = "0.1.0"

    def __init__(self, work_dir: str):
        super().__init__(work_dir)
        self._binary_path = self._find_binary()

    def _find_binary(self) -> str:
        """Find the medusa binary in PATH or common locations."""
        candidates = [
            "medusa",
            os.path.expanduser("~/go/bin/medusa"),
        ]
        for c in candidates:
            try:
                result = subprocess.run([c, "--version"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return c
            except Exception:
                continue
        return "medusa"

    def check_dependencies(self) -> bool:
        """Check if medusa binary is available."""
        try:
            result = subprocess.run(
                [self._binary_path, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_version(self) -> str:
        """Get installed Medusa version."""
        try:
            result = subprocess.run(
                [self._binary_path, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def build_command(self, target_dir: str, **kwargs) -> list[str]:
        """Build the Medusa command.
        
        Medusa requires a config file (medusa.json) in the target directory.
        """
        cmd = [self._binary_path, "fuzz"]
        
        # Config file path
        config = kwargs.get("config")
        if config:
            cmd.extend(["--config", config])
        else:
            # Default: look for medusa.json in target
            config_path = Path(target_dir) / "medusa.json"
            if config_path.exists():
                cmd.extend(["--config", str(config_path)])
        
        # Workers
        workers = kwargs.get("workers")
        if workers:
            cmd.extend(["--workers", str(workers)])
        
        # Test limit
        test_limit = kwargs.get("test_limit")
        if test_limit:
            cmd.extend(["--test-limit", str(test_limit)])
        
        # Timeout
        timeout = kwargs.get("fuzz_timeout")
        if timeout:
            cmd.extend(["--timeout", str(timeout)])
        
        # Sequence length
        seq_len = kwargs.get("sequence_length")
        if seq_len:
            cmd.extend(["--seq-len", str(seq_len)])
        
        # Corpus directory
        corpus_dir = kwargs.get("corpus_dir")
        if corpus_dir:
            cmd.extend(["--corpus-dir", corpus_dir])
        
        # Target directory
        cmd.append(target_dir)
        
        return cmd

    def run(self, target_dir: str, job_id: str, timeout_s: int = 1200,
            **kwargs) -> AdapterResult:
        """
        Run Medusa and preserve corpus + failing sequences.
        
        Extends base run() with corpus preservation logic.
        """
        if not self.check_dependencies():
            return AdapterResult(
                success=False, tool="Medusa", tool_version="",
                adapter_version=self.ADAPTER_VERSION,
                command="", exit_code=-1, timed_out=False,
                stdout="", stderr="", raw_output_paths=[],
                error="Medusa not found in PATH",
            )

        tool_version = self.get_version()
        cmd = self.build_command(target_dir, **kwargs)
        cmd_str = " ".join(str(c) for c in cmd)

        # Record pre-campaign corpus hash
        initial_corpus_hash = self._hash_corpus(target_dir, kwargs.get("corpus_dir"))

        try:
            start = time.time()
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

        duration = time.time() - start

        # Save raw output
        output_paths = []
        if stdout:
            out_path = str(self.work_dir / f"{job_id}_medusa_stdout.txt")
            Path(out_path).write_text(stdout)
            output_paths.append(out_path)
        if stderr:
            err_path = str(self.work_dir / f"{job_id}_medusa_stderr.txt")
            Path(err_path).write_text(stderr)
            output_paths.append(err_path)

        # Preserve corpus
        corpus_archive_path = self._archive_corpus(target_dir, job_id, kwargs.get("corpus_dir"))
        if corpus_archive_path:
            output_paths.append(corpus_archive_path)

        # Record final corpus hash
        final_corpus_hash = self._hash_corpus(target_dir, kwargs.get("corpus_dir"))

        # Parse output
        normalized = []
        if stdout:
            normalized = self.parse_output(stdout, stderr, output_paths)

        # Build execution context
        execution_context = {
            "tool_version": tool_version,
            "adapter_version": self.ADAPTER_VERSION,
            "command": cmd_str,
            "duration_seconds": duration,
            "exit_code": exit_code,
            "timed_out": timed_out,
            "initial_corpus_hash": initial_corpus_hash,
            "final_corpus_hash": final_corpus_hash,
            "corpus_archive": corpus_archive_path or "",
            "worker_count": kwargs.get("workers", 0),
            "test_limit": kwargs.get("test_limit", 0),
            "sequence_length": kwargs.get("sequence_length", 0),
            "machine_profile": "unknown",
        }

        # Also save execution context as JSON
        ctx_path = str(self.work_dir / f"{job_id}_medusa_context.json")
        Path(ctx_path).write_text(json.dumps(execution_context, indent=2))
        output_paths.append(ctx_path)

        success = exit_code == 0 or len(normalized) > 0

        result_obj = AdapterResult(
            success=success,
            tool="Medusa",
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
        )
        result_obj.execution_manifest = execution_context
        return result_obj

    def parse_output(self, stdout: str, stderr: str, output_paths: list[str]) -> list[dict]:
        """Parse Medusa output for failing sequences and invariant violations."""
        findings = []
        
        # Medusa outputs failing sequences to stdout
        # Look for patterns like "FAILED" or "Invariant failed"
        lines = stdout.split("\n")
        current_test = ""
        failing_sequence = []
        in_sequence = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # Test result line
            if "FAILED" in line_stripped or "failing" in line_stripped.lower():
                current_test = line_stripped
                in_sequence = True
                failing_sequence = []
            
            # Sequence lines (TRACE or numbered steps)
            if in_sequence and line_stripped:
                if line_stripped.startswith("TRACE") or line_stripped.startswith("["):
                    failing_sequence.append(line_stripped)
                elif line_stripped.startswith("=>") or line_stripped.startswith("  -"):
                    failing_sequence.append(line_stripped)
            
            # End of sequence marker
            if in_sequence and ("PASSED" in line_stripped or "Test limit" in line_stripped):
                if current_test and failing_sequence:
                    findings.append({
                        "finding_id": str(uuid.uuid4()),
                        "classification": "invariant_violation",
                        "severity": "high",
                        "confidence": {"level": 3, "evidence_level": "executable_failure",
                                       "evidence_sources": ["medusa"]},
                        "tool": {"name": "medusa", "version": self.get_version(),
                                 "rule_id": "fuzzer-failure"},
                        "location": {"file": "", "start_line": 0},
                        "vulnerability_category": "other",
                        "title": f"Medusa: {current_test[:100]}",
                        "description": f"Failing sequence:\n" + "\n".join(failing_sequence[-20:]),
                        "deduplication_group": f"medusa-fail-{current_test[:50]}",
                        "reproduction": {"status": "none"},
                        "schema_version": "1.0.0",
                    })
                current_test = ""
                failing_sequence = []
                in_sequence = False
        
        # Also look for crash/panic detection
        if "panic" in stdout.lower() or "assertion" in stdout.lower():
            findings.append({
                "finding_id": str(uuid.uuid4()),
                "classification": "invariant_violation",
                "severity": "high",
                "tool": {"name": "medusa", "version": self.get_version(), "rule_id": "panic-detected"},
                "location": {"file": "", "start_line": 0},
                "vulnerability_category": "logic_error",
                "title": "Medusa: Panic/assertion violation detected",
                "description": stdout[-500:] if len(stdout) > 500 else stdout,
                "deduplication_group": "medusa-panic",
                "reproduction": {"status": "none"},
                "schema_version": "1.0.0",
            })
        
        return findings

    def _hash_corpus(self, target_dir: str, corpus_dir: Optional[str] = None) -> str:
        """Compute a hash of the corpus directory contents."""
        base = Path(corpus_dir) if corpus_dir else Path(target_dir) / "corpus"
        if not base.exists():
            return ""
        
        import hashlib
        hasher = hashlib.sha256()
        
        # Hash all files in the corpus
        for f in sorted(base.rglob("*")):
            if f.is_file():
                try:
                    hasher.update(f.name.encode())
                    hasher.update(f.read_bytes()[:4096])  # First 4KB per file
                except Exception:
                    continue
        
        return hasher.hexdigest()[:16]

    def _archive_corpus(self, target_dir: str, job_id: str,
                        corpus_dir: Optional[str] = None) -> Optional[str]:
        """Archive the corpus directory."""
        base = Path(corpus_dir) if corpus_dir else Path(target_dir) / "corpus"
        if not base.exists():
            return None
        
        archive_path = str(self.work_dir / f"{job_id}_corpus.tar.gz")
        shutil.make_archive(
            archive_path.replace(".tar.gz", ""),
            "gztar",
            str(base),
        )
        return archive_path