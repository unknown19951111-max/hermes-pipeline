"""
Invariant registry — query, select, filter, and manage the invariant library.
"""

import json
import os
from pathlib import Path
from typing import Optional


class InvariantRegistry:
    """Versioned registry of security invariants with query and selection."""

    def __init__(self, registry_path: str):
        self.registry_path = Path(registry_path)
        self._data = self._load()

    def _load(self) -> dict:
        if not self.registry_path.exists():
            return {"_meta": {"registry_version": "1.0.0", "invariants": []}}
        return json.loads(self.registry_path.read_text())

    def reload(self):
        """Reload registry from disk."""
        self._data = self._load()

    def list_invariants(self, status: Optional[str] = None,
                        archetype: Optional[str] = None) -> list[dict]:
        """List invariants, optionally filtered by status and/or archetype."""
        results = []
        for inv in self._data.get("invariants", []):
            if status and inv.get("status") != status:
                continue
            if archetype and archetype not in inv.get("archetype", ""):
                continue
            results.append(inv)
        return results

    def select_for_archetype(self, archetypes: list[str],
                             min_status: str = "CANDIDATE") -> list[dict]:
        """
        Select compatible invariants for the given archetype(s).
        
        Selection rules:
        - Must match at least one archetype
        - Must meet minimum status threshold
        - Must not be DEPRECATED (unless explicitly requested)
        - If multiple archetypes match, deduplicate by invariant ID
        - Prefer VERIFIED invariants over CANDIDATE ones
        """
        status_rank = {"CANDIDATE": 0, "VERIFIED": 1, "DEPRECATED": -1}
        min_rank = status_rank.get(min_status, 0)

        seen_ids = set()
        selected = []

        for inv in self._data.get("invariants", []):
            inv_id = inv.get("id", "")
            inv_status = inv.get("status", "CANDIDATE")
            inv_archetype = inv.get("archetype", "")

            if status_rank.get(inv_status, 0) < min_rank:
                continue

            # Check if this invariant's archetype matches any of the target archetypes
            if any(a in archetypes or inv_archetype in archetypes for a in [inv_archetype]):
                if inv_id not in seen_ids:
                    seen_ids.add(inv_id)
                    selected.append(inv)

        # Sort: VERIFIED first, then CANDIDATE
        selected.sort(key=lambda x: status_rank.get(x.get("status", "CANDIDATE"), 0), reverse=True)
        return selected

    def get_invariant(self, invariant_id: str) -> Optional[dict]:
        """Get a single invariant by ID."""
        for inv in self._data.get("invariants", []):
            if inv.get("id") == invariant_id:
                return inv
        return None

    def get_required_dependencies(self, archetypes: list[str]) -> list[str]:
        """Collect all required dependencies for a set of archetypes."""
        deps = set()
        invariants = self.select_for_archetype(archetypes)
        for inv in invariants:
            for dep in inv.get("required_dependencies", []):
                deps.add(dep)
        return sorted(deps)

    def check_compatibility(self, invariant_id: str,
                            compiler_version: str = "0.8.20",
                            available_deps: Optional[list[str]] = None) -> tuple[bool, list[str]]:
        """
        Check if an invariant is compatible with the target environment.
        
        Returns: (compatible, [reasons if incompatible])
        """
        inv = self.get_invariant(invariant_id)
        if not inv:
            return False, [f"Invariant not found: {invariant_id}"]

        reasons = []

        # Check compiler version
        compat = inv.get("solc_compatibility", "")
        if compat and compat.startswith(">="):
            min_ver = compat.replace(">=", "").strip()
            if self._compare_versions(compiler_version, min_ver) < 0:
                reasons.append(f"Compiler {compiler_version} < required {compat}")

        # Check dependencies
        required_deps = inv.get("required_dependencies", [])
        if available_deps and required_deps:
            for dep in required_deps:
                if dep not in available_deps:
                    reasons.append(f"Missing dependency: {dep}")

        return len(reasons) == 0, reasons

    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        """Compare two version strings. Returns -1, 0, or 1."""
        try:
            v1_parts = [int(p) for p in v1.split(".")[:3]]
            v2_parts = [int(p) for p in v2.split(".")[:3]]
            for a, b in zip(v1_parts, v2_parts):
                if a < b:
                    return -1
                elif a > b:
                    return 1
            return 0
        except (ValueError, IndexError):
            return 0

    def can_promote_to_verified(self, invariant_id: str) -> tuple[bool, list[str]]:
        """
        Check if an invariant has all required evidence for VERIFIED status.
        
        VERIFIED requires:
        - implementation_path (non-empty)
        - source_commit (non-empty)
        - positive_cases (non-empty list)
        - negative_cases (non-empty list)
        - validation_command (non-empty)
        - validation_artifacts (non-empty)
        - reviewer (non-empty)
        - review_timestamp (non-empty)
        """
        inv = self.get_invariant(invariant_id)
        if not inv:
            return False, [f"Invariant not found: {invariant_id}"]

        reasons = []
        required_evidence = [
            ("implementation_path", "No implementation path"),
            ("source_commit", "No source commit"),
            ("positive_cases", "No positive test cases"),
            ("negative_cases", "No negative test cases"),
            ("validation_command", "No validation command"),
            ("validation_artifacts", "No validation artifacts"),
            ("reviewer", "No reviewer"),
            ("review_timestamp", "No review timestamp"),
        ]
        for field, msg in required_evidence:
            val = inv.get(field, "")
            if not val or (isinstance(val, list) and len(val) == 0):
                reasons.append(msg)

        return len(reasons) == 0, reasons

    def promote(self, invariant_id: str, new_status: str,
                commit: str = "") -> bool:
        """
        Promote an invariant to a new status (CANDIDATE → VERIFIED, etc.).
        
        Rules:
        - VERIFIED is immutable — requires version bump
        - Never demote without explicit action
        - Promotion to VERIFIED requires full evidence (use can_promote_to_verified)
        """
        if new_status not in ["CANDIDATE", "VERIFIED", "DEPRECATED"]:
            raise ValueError(f"Invalid status: {new_status}")
        
        if new_status == "VERIFIED":
            ok, reasons = self.can_promote_to_verified(invariant_id)
            if not ok:
                raise ValueError(f"Cannot promote {invariant_id} to VERIFIED: {'; '.join(reasons)}")

        for i, inv in enumerate(self._data.get("invariants", [])):
            if inv.get("id") == invariant_id:
                if inv.get("status") == "VERIFIED" and new_status != "DEPRECATED":
                    # VERIFIED is immutable — create a new version instead
                    raise ValueError(
                        f"Cannot modify VERIFIED invariant {invariant_id}. "
                        f"Create a new version with bumped version field."
                    )
                self._data["invariants"][i]["status"] = new_status
                if commit:
                    self._data["invariants"][i]["source_commit"] = commit
                self._save()
                return True

        raise ValueError(f"Invariant not found: {invariant_id}")

    def _save(self):
        """Persist registry to disk."""
        self.registry_path.write_text(json.dumps(self._data, indent=2))

    @property
    def count(self) -> dict:
        """Get invariant count by status."""
        counts = {"VERIFIED": 0, "CANDIDATE": 0, "DEPRECATED": 0, "TOTAL": 0}
        for inv in self._data.get("invariants", []):
            status = inv.get("status", "CANDIDATE")
            if status in counts:
                counts[status] += 1
            counts["TOTAL"] += 1
        return counts