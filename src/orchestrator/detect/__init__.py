"""Ecosystem and framework detection — deterministic evidence-based classification."""

import json
import os
import re
from pathlib import Path
from typing import Optional


class DetectionError(Exception):
    pass


class DetectionResult:
    """Evidence-based detection result."""

    def __init__(self, ecosystem: str, framework: str, confidence: float,
                 evidence: list, conflicts: list, missing: list,
                 detection_method: str):
        self.ecosystem = ecosystem
        self.framework = framework
        self.confidence = confidence
        self.evidence = evidence
        self.conflicts = conflicts
        self.missing = missing
        self.detection_method = detection_method

    def to_dict(self) -> dict:
        return {
            "ecosystem": self.ecosystem,
            "framework": self.framework,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "conflicts": self.conflicts,
            "missing": self.missing,
            "detection_method": self.detection_method,
        }


class FrameworkDetector:
    """Deterministic framework and ecosystem detector based on project files."""

    DETECTION_RULES = {
        "foundry": {
            "files": ["foundry.toml", "foundry.toml.ci"],
            "dirs": ["lib"],
            "config_keys": ["[profile]", "[fmt]", "[fuzz]", "[invariant]"],
        },
        "hardhat": {
            "files": ["hardhat.config.js", "hardhat.config.ts", "hardhat.config.cjs"],
            "dirs": ["artifacts", "cache"],
        },
        "truffle": {
            "files": ["truffle-config.js", "truffle.js"],
            "dirs": [],
        },
        "dapptools": {
            "files": ["dapp.json", "Makefile"],
            "dirs": ["src", "dapp", "lib"],
        },
        "brownie": {
            "files": ["brownie-config.yaml", "brownie-config.yml"],
            "dirs": ["build", "contracts", "interfaces"],
        },
        "anchor": {
            "files": ["Anchor.toml"],
            "dirs": ["programs", "tests", "migrations"],
            "config_keys": ["[tool.anchor]", "[provider]", "[programs]"],
        },
        "solana_native": {
            "files": ["Cargo.toml"],
            "dirs": ["src/lib.rs"],
            "config_keys": ["solana-program"],
        },
        "aptos": {
            "files": ["Move.toml", "Aptos.toml"],
            "dirs": ["sources", "tests"],
            "config_keys": ["AptosFramework", "aptos_std"],
        },
        "sui": {
            "files": ["Move.toml", "sui.yaml", "sui.toml"],
            "dirs": ["sources", "tests"],
            "config_keys": ["SuiFramework", "sui_framework"],
        },
    }

    ECOSYSTEM_PATTERNS = {
        "evm": [".sol", ".vy", ".yul"],
        "solana": [".rs", ".so"],
        "move": [".move"],
        "rust": [".rs", "Cargo.toml"],
        "javascript": [".js", ".ts", "package.json"],
        "python": [".py", "requirements.txt", "Pipfile"],
    }

    def __init__(self, project_root: str):
        self.root = Path(project_root)

    def detect_ecosystem(self) -> DetectionResult:
        """Detect the blockchain ecosystem based on file extensions and config files."""
        evidence = []
        conflicts = []
        missing = []
        scores = {"evm": 0, "solana": 0, "move": 0}

        for f in self.root.rglob("*"):
            if not f.is_file() or f.name.startswith("."):
                continue
            for eco, exts in self.ECOSYSTEM_PATTERNS.items():
                if any(f.name.endswith(ext) for ext in exts):
                    if eco == "evm":
                        scores["evm"] += 1
                    elif eco == "solana" and f.suffix == ".so":
                        scores["solana"] += 1
                    elif eco == "move":
                        scores["move"] += 1

        sol_files = list(self.root.rglob("*.sol"))
        if sol_files:
            evidence.append(f"Found {len(sol_files)} .sol files")
            scores["evm"] += 10

        for config_name in ["foundry.toml", "hardhat.config.js", "hardhat.config.ts",
                           "truffle-config.js", "brownie-config.yaml"]:
            if (self.root / config_name).exists():
                scores["evm"] += 20
                evidence.append(f"Found EVM config: {config_name}")

        anchor_toml = self.root / "Anchor.toml"
        if anchor_toml.exists():
            scores["solana"] += 20
            evidence.append("Found Anchor.toml (Solana)")

        move_toml = self.root / "Move.toml"
        if move_toml.exists():
            scores["move"] += 20
            evidence.append("Found Move.toml")

        # Check for Aptos config
        if (self.root / "Aptos.toml").exists():
            scores["move"] += 20
            evidence.append("Found Aptos.toml")

        # Check for Sui config
        if (self.root / "sui.yaml").exists() or (self.root / "sui.toml").exists():
            scores["move"] += 20
            evidence.append("Found Sui config")

        total = sum(scores.values())
        if total == 0:
            return DetectionResult(
                ecosystem="unknown", framework="unknown", confidence=0.0,
                evidence=evidence, conflicts=conflicts, missing=["No ecosystem indicators found"],
                detection_method="file_analysis"
            )

        winner = max(scores, key=scores.get)
        winner_score = scores[winner]
        second_score = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0
        confidence = min(1.0, winner_score / max(total, 1))

        if second_score > 0 and second_score >= winner_score * 0.5:
            conflicts.append(f"Ambiguous: {winner}={winner_score}, next={second_score}")

        return DetectionResult(
            ecosystem="evm" if winner == "evm" else winner,
            framework="unknown",
            confidence=confidence,
            evidence=evidence,
            conflicts=conflicts,
            missing=missing,
            detection_method="file_analysis"
        )

    def detect_framework(self) -> DetectionResult:
        """Detect the build framework deterministically."""
        evidence = []
        conflicts = []
        missing = []
        detected_frameworks = []
        scores = {}

        for framework, rules in self.DETECTION_RULES.items():
            score = 0
            for fname in rules["files"]:
                if (self.root / fname).exists():
                    score += 20
                    evidence.append(f"Found {fname}")
            for dname in rules["dirs"]:
                if (self.root / dname).is_dir():
                    score += 5
                    evidence.append(f"Found {dname}/ directory")
            if score > 0:
                scores[framework] = score
                detected_frameworks.append(framework)

        # Foundry
        if (self.root / "foundry.toml").exists():
            evidence.append("foundry.toml detected → Foundry framework")
            return DetectionResult(
                ecosystem="evm", framework="foundry", confidence=0.95,
                evidence=evidence, conflicts=[], missing=[],
                detection_method="manifest_analysis"
            )

        # Hardhat
        for hc in ["hardhat.config.js", "hardhat.config.ts"]:
            if (self.root / hc).exists():
                evidence.append(f"{hc} detected → Hardhat framework")
                return DetectionResult(
                    ecosystem="evm", framework="hardhat", confidence=0.95,
                    evidence=evidence, conflicts=[], missing=[],
                    detection_method="manifest_analysis"
                )

        # Anchor (Solana)
        if (self.root / "Anchor.toml").exists():
            evidence.append("Anchor.toml detected → Anchor framework (Solana)")
            return DetectionResult(
                ecosystem="solana", framework="anchor", confidence=0.95,
                evidence=evidence, conflicts=[], missing=[],
                detection_method="manifest_analysis"
            )

        # Aptos (Move)
        if (self.root / "Aptos.toml").exists():
            evidence.append("Aptos.toml detected → Aptos framework (Move)")
            return DetectionResult(
                ecosystem="move", framework="aptos", confidence=0.95,
                evidence=evidence, conflicts=[], missing=[],
                detection_method="manifest_analysis"
            )

        # Sui (Move)
        if (self.root / "sui.yaml").exists() or (self.root / "sui.toml").exists():
            evidence.append("Sui config detected → Sui framework (Move)")
            return DetectionResult(
                ecosystem="move", framework="sui", confidence=0.95,
                evidence=evidence, conflicts=[], missing=[],
                detection_method="manifest_analysis"
            )

        if detected_frameworks:
            winner = max(scores, key=scores.get)
            eco = "evm"
            if winner in ("anchor", "solana_native"):
                eco = "solana"
            elif winner in ("aptos", "sui"):
                eco = "move"
            for fw in detected_frameworks:
                if fw != winner and scores[fw] >= scores[winner] * 0.5:
                    conflicts.append(f"Ambiguous framework: {fw} ({scores[fw]}) vs {winner} ({scores[winner]})")
            return DetectionResult(
                ecosystem=eco, framework=winner,
                confidence=0.7 if not conflicts else 0.5,
                evidence=evidence, conflicts=conflicts, missing=missing,
                detection_method="score_analysis"
            )

        sol_files = list(self.root.rglob("*.sol"))
        if sol_files:
            evidence.append(f"No framework config but {len(sol_files)} .sol files present")
            missing.append("No recognized framework configuration found")
            return DetectionResult(
                ecosystem="evm", framework="standard",
                confidence=0.3, evidence=evidence, conflicts=[], missing=missing,
                detection_method="fallback"
            )

        # Check for Move files as final non-EVM fallback
        move_files = list(self.root.rglob("*.move"))
        if move_files:
            evidence.append(f"No framework config but {len(move_files)} .move files present")
            missing.append("No recognized Move framework detected (sources only)")
            return DetectionResult(
                ecosystem="move", framework="unknown",
                confidence=0.3, evidence=evidence, conflicts=[], missing=missing,
                detection_method="fallback"
            )

        # Check for Solana Rust files as non-EVM fallback
        cargo_toml = self.root / "Cargo.toml"
        if cargo_toml.exists():
            content = cargo_toml.read_text()
            if "solana" in content.lower():
                evidence.append("Cargo.toml with solana dependency detected")
                return DetectionResult(
                    ecosystem="solana", framework="solana_native",
                    confidence=0.5, evidence=evidence, conflicts=[], missing=missing,
                    detection_method="score_analysis"
                )

        return DetectionResult(
            ecosystem="unknown", framework="unknown", confidence=0.0,
            evidence=evidence, conflicts=[],
            missing=["No framework files found"],
            detection_method="fallback"
        )