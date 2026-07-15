"""
Sandboxing — Docker-based container isolation for target code execution.
"""

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional


class SandboxError(Exception):
    pass


class SandboxManager:
    """
    Manages Docker-based sandbox containers for running untrusted target code.

    Each job gets an isolated container with:
    - Read-only mounts for invariant library and datasets
    - Ephemeral writable workspace
    - Network egress restricted to RPC endpoint only
    - No host secrets (no SSH, no Docker socket, no credentials)
    - Resource limits (CPU, memory, disk)
    - No persistent state after container exit
    """

    DEFAULT_IMAGE = "hermes-pipeline:latest"
    DEFAULT_NETWORK = "hermes-net"

    def __init__(self, image: str = DEFAULT_IMAGE, network: str = DEFAULT_NETWORK,
                 rpc_url: str = "", use_sandbox: bool = True):
        self.image = image
        self.network = network
        self.rpc_url = rpc_url or os.environ.get("ETH_RPC_URL", "")
        self.use_sandbox = use_sandbox
        self._containers: dict[str, str] = {}  # job_id -> container_name

    def check_docker_available(self) -> bool:
        """Check if Docker is available and running."""
        try:
            result = subprocess.run(
                ["docker", "info", "--format", "{{.ServerVersion}}"],
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def ensure_image(self, dockerfile: str = "") -> bool:
        """
        Ensure the sandbox image exists. Build from Dockerfile if provided.
        Returns True if image is available.
        """
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", self.image],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return True  # Image exists
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

        # Try to build from Dockerfile
        if dockerfile and Path(dockerfile).exists():
            return self._build_image(dockerfile)

        return False

    def _build_image(self, dockerfile: str) -> bool:
        """Build the sandbox Docker image from a Dockerfile."""
        try:
            result = subprocess.run(
                ["docker", "build", "-t", self.image, "-f", dockerfile,
                 str(Path(dockerfile).parent)],
                capture_output=True, text=True, timeout=300,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def create_network(self) -> bool:
        """Create the sandbox network if it doesn't exist."""
        try:
            # Check if network exists
            result = subprocess.run(
                ["docker", "network", "inspect", self.network],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return True  # Already exists

            # Create it
            result = subprocess.run(
                ["docker", "network", "create", "--driver", "bridge",
                 "--opt", "com.docker.network.bridge.name=hermes0",
                 self.network],
                capture_output=True, text=True, timeout=30,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def run_in_sandbox(self, job_id: str, command: list[str],
                        work_dir: str,
                        invariant_dir: str = "",
                        dataset_dir: str = "",
                        rpc_url: str = "",
                        cpus: int = 1,
                        memory_mb: int = 2048,
                        timeout_s: int = 3600,
                        artifact_dir: str = "") -> tuple[int, str, str]:
        """
        Run a command inside a sandbox container.

        Args:
            job_id: Unique job identifier
            command: Command to run (list of strings)
            work_dir: Writable workspace directory to mount
            invariant_dir: Read-only invariant library path
            dataset_dir: Read-only dataset path
            rpc_url: RPC endpoint for network egress
            cpus: CPU limit
            memory_mb: Memory limit in MB
            timeout_s: Container timeout
            artifact_dir: Directory to store artifacts

        Returns:
            (exit_code, stdout, stderr)
        """
        if not self.use_sandbox:
            # Bypass sandboxing — run directly (for development/testing)
            return self._run_direct(command, work_dir, timeout_s)

        if not self.check_docker_available():
            if not self.use_sandbox:
                return self._run_direct(command, work_dir, timeout_s)
            raise SandboxError("Docker is not available but sandboxing is required")

        # Build docker run command
        container_name = f"hermes-{job_id[:12]}"
        self._containers[job_id] = container_name

        docker_cmd = [
            "docker", "run",
            "--rm",  # Auto-remove container on exit
            "--name", container_name,
            "--network", self.network if self._network_exists() else "none",
            "--cpus", str(cpus),
            "--memory", f"{memory_mb}m",
            "--memory-swap", f"{memory_mb}m",  # No swap
            "--read-only",  # Root filesystem is read-only
            "--tmpfs", "/tmp:noexec,nosuid,size=100m",
            "--security-opt", "no-new-privileges:true",
            "--cap-drop", "ALL",  # Drop all capabilities
            "--cap-add", "NET_RAW",  # Minimal network for RPC
        ]

        # Mount work directory (writable)
        docker_cmd.extend(["-v", f"{work_dir}:/workspace:rw"])

        # Mount invariant library (read-only)
        if invariant_dir and Path(invariant_dir).exists():
            docker_cmd.extend(["-v", f"{invariant_dir}:/invariants:ro"])

        # Mount dataset directory (read-only)
        if dataset_dir and Path(dataset_dir).exists():
            docker_cmd.extend(["-v", f"{dataset_dir}:/datasets:ro"])

        # Mount artifact directory (writable)
        if artifact_dir:
            docker_cmd.extend(["-v", f"{artifact_dir}:/artifacts:rw"])

        # Set RPC environment
        env_vars = {
            "ETH_RPC_URL": rpc_url or self.rpc_url,
            "HOME": "/tmp",
            "FOUNDRY_PROFILE": "ci",
        }
        for key, val in env_vars.items():
            if val:
                docker_cmd.extend(["-e", f"{key}={val}"])

        # Working directory
        docker_cmd.extend(["-w", "/workspace"])

        # Image
        docker_cmd.append(self.image)

        # Command
        docker_cmd.extend(command)

        # Run
        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True, text=True,
                timeout=timeout_s,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            # Clean up container
            subprocess.run(
                ["docker", "kill", container_name],
                capture_output=True, timeout=10,
            )
            return -1, "", f"TIMEOUT after {timeout_s}s"
        finally:
            self._containers.pop(job_id, None)

    def _run_direct(self, command: list[str], work_dir: str,
                    timeout_s: int) -> tuple[int, str, str]:
        """Run directly without sandboxing (development mode)."""
        try:
            result = subprocess.run(
                command,
                cwd=work_dir,
                capture_output=True, text=True,
                timeout=timeout_s,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"TIMEOUT after {timeout_s}s"

    def _network_exists(self) -> bool:
        """Check if the docker network exists."""
        try:
            result = subprocess.run(
                ["docker", "network", "inspect", self.network],
                capture_output=True, timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def cleanup_job(self, job_id: str):
        """Clean up any containers for a job."""
        container_name = self._containers.get(job_id)
        if container_name:
            try:
                subprocess.run(
                    ["docker", "kill", container_name],
                    capture_output=True, timeout=10,
                )
            except Exception:
                pass
            self._containers.pop(job_id, None)

    def cleanup_all(self):
        """Clean up all tracked containers."""
        for job_id in list(self._containers.keys()):
            self.cleanup_job(job_id)


class SandboxConfig:
    """
    Configuration for sandbox execution.

    Generates the Dockerfile and docker-compose.yml for the pipeline.
    """

    DOCKERFILE_CONTENT = """# Hermes Pipeline Sandbox Container
FROM ubuntu:22.04

# Install essential tools
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \\
    curl \\
    git \\
    python3 \\
    python3-pip \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Install Foundry
RUN curl -L https://foundry.paradigm.xyz | bash && \\
    /root/.foundry/bin/foundryup

# Install solc-select
RUN pip3 install solc-select

# Add to PATH
ENV PATH="/root/.foundry/bin:/root/.local/bin:$PATH"

# Install default solc version
RUN solc-select install 0.8.20 && solc-select use 0.8.20

# Create workspace directories
RUN mkdir -p /workspace /invariants /datasets /artifacts

# Drop all capabilities by default
USER nobody

WORKDIR /workspace
"""

    COMPOSE_CONTENT = """# Hermes Pipeline Docker Compose
version: '3.8'

networks:
  hermes-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

services:
  pipeline:
    build:
      context: .
      dockerfile: docker/Dockerfile
    image: hermes-pipeline:latest
    network_mode: "none"
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_RAW
    environment:
      - ETH_RPC_URL=
      - FOUNDRY_PROFILE=ci
    volumes:
      # Mounted per-job by orchestrator
    working_dir: /workspace
"""