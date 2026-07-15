"""
Program eligibility gate — GATE ZERO. Determines whether a target is eligible for
bounty hunting before expensive analysis runs.

This gate is separate from technical classification. It deals with program-level
economics: does this program pay for Medium findings?
"""

import json
import re
from datetime import datetime, timezone
from typing import Optional


# GATE ZERO results
ELIGIBLE = "ELIGIBLE"
INELIGIBLE = "INELIGIBLE"
AMBIGUOUS_REQUIRES_REVIEW = "AMBIGUOUS_REQUIRES_REVIEW"
NO_PROGRAM_METADATA = "NO_PROGRAM_METADATA"


class EligibilityError(Exception):
    pass


class EligibilitySnapshot:
    """Immutable eligibility snapshot for a bounty program."""

    SCHEMA_VERSION = "1.0.0"

    def __init__(self, data: dict):
        self.data = data
        self._validate()

    def _validate(self):
        required = ["program_name", "date_checked", "status", "result"]
        for field in required:
            if field not in self.data:
                raise EligibilityError(f"Missing required field: {field}")

    def to_dict(self) -> dict:
        return dict(self.data)

    def to_json(self) -> str:
        return json.dumps(self.data, indent=2, default=str)

    @classmethod
    def create(cls, program_name: str, official_url: str,
               result: str, **kwargs) -> "EligibilitySnapshot":
        data = {
            "program_name": program_name,
            "official_url": official_url,
            "date_checked": datetime.now(timezone.utc).isoformat(),
            "result": result,
            "program_status": kwargs.get("program_status", ""),
            "scope_repositories": kwargs.get("scope_repositories", []),
            "scope_contracts": kwargs.get("scope_contracts", []),
            "scope_chains": kwargs.get("scope_chains", []),
            "explicit_inclusions": kwargs.get("explicit_inclusions", []),
            "explicit_exclusions": kwargs.get("explicit_exclusions", []),
            "required_poc_conditions": kwargs.get("required_poc_conditions", ""),
            "reward_table": kwargs.get("reward_table", {}),
            "severity_definitions": kwargs.get("severity_definitions", {}),
            "pays_for_medium": kwargs.get("pays_for_medium", False),
            "minimum_reward": kwargs.get("minimum_reward", 0),
            "maximum_reward": kwargs.get("maximum_reward", 0),
            "kyc_required": kwargs.get("kyc_required", False),
            "kyc_restrictions": kwargs.get("kyc_restrictions", ""),
            "jurisdiction_restrictions": kwargs.get("jurisdiction_restrictions", ""),
            "submission_restrictions": kwargs.get("submission_restrictions", ""),
            "manual_overrides": kwargs.get("manual_overrides", {}),
            "snapshot_hash": kwargs.get("snapshot_hash", ""),
            "schema_version": cls.SCHEMA_VERSION,
        }
        return cls(data)


class EligibilityGate:
    """
    GATE ZERO — determines if a program pays for Medium findings.
    
    This gate operates on deterministic rules and preserved evidence.
    It does NOT use LLM guessing for eligibility decisions.
    """

    def __init__(self, program_data_dir: str = ""):
        self.program_data_dir = program_data_dir

    def evaluate(self, program_name: str = "",
                 program_url: str = "",
                 known_data: Optional[dict] = None) -> EligibilitySnapshot:
        """
        Evaluate program eligibility.
        
        Uses available data sources in priority order:
        1. Known/verified program data (provided via known_data)
        2. Locally cached program data
        3. Returns NO_PROGRAM_METADATA if no data available
        
        This function does NOT scrape live web pages — scraping is a separate
        step that should be performed by a verified web-extraction component
        before calling this gate.
        """
        if known_data:
            return self._evaluate_from_data(program_name, program_url, known_data)

        if self.program_data_dir:
            cached = self._load_cached(program_name)
            if cached:
                return self._evaluate_from_data(program_name, program_url, cached)

        # No data available — return NO_PROGRAM_METADATA
        return EligibilitySnapshot.create(
            program_name=program_name or "unknown",
            official_url=program_url or "",
            result=NO_PROGRAM_METADATA,
            notes=["No program eligibility data available. "
                    "GATE ZERO cannot make a determination."],
        )

    def _evaluate_from_data(self, program_name: str,
                            program_url: str,
                            data: dict) -> EligibilitySnapshot:
        """Evaluate eligibility from provided program data."""
        pays_for_medium = data.get("pays_for_medium", False)
        reward_table = data.get("reward_table", {})
        program_status = data.get("status", "unknown")

        # Determine result
        if program_status == "closed" or program_status == "inactive":
            result = INELIGIBLE
        elif pays_for_medium:
            result = ELIGIBLE
        elif not pays_for_medium and bool(reward_table):
            # Has a reward table but doesn't pay for Medium
            result = INELIGIBLE
        elif not reward_table and not pays_for_medium:
            result = AMBIGUOUS_REQUIRES_REVIEW
        else:
            result = AMBIGUOUS_REQUIRES_REVIEW

        return EligibilitySnapshot.create(
            program_name=program_name or data.get("name", "unknown"),
            official_url=program_url or data.get("url", ""),
            result=result,
            program_status=program_status,
            reward_table=reward_table,
            pays_for_medium=pays_for_medium,
            minimum_reward=data.get("minimum_reward", 0),
            maximum_reward=data.get("maximum_reward", 0),
            kyc_required=data.get("kyc_required", False),
            kyc_restrictions=data.get("kyc_restrictions", ""),
            jurisdiction_restrictions=data.get("jurisdiction_restrictions", ""),
        )

    def _load_cached(self, program_name: str) -> Optional[dict]:
        """Load cached program data from local storage."""
        import os
        import json
        from pathlib import Path

        if not self.program_data_dir:
            return None

        cache_path = Path(self.program_data_dir) / f"{program_name.lower().replace(' ', '-')}.json"
        if cache_path.exists():
            try:
                return json.loads(cache_path.read_text())
            except Exception:
                return None

        # Try scanning for any file with matching name
        for f in Path(self.program_data_dir).glob("*.json"):
            try:
                data = json.loads(f.read_text())
                if data.get("name", "").lower() == program_name.lower():
                    return data
            except Exception:
                continue

        return None

    @staticmethod
    def parse_reward_table(text: str) -> dict:
        """
        Parse a reward table from free text into structured data.
        
        This is a best-effort parser. It extracts severity→reward mappings
        from common formats like:
        - "High: up to $50,000, Medium: up to $5,000"
        - "Critical: $100k, High: $50k, Medium: $10k"
        """
        rewards = {}
        pattern = re.compile(
            r'(Critical|High|Medium|Low|Informational)\s*[:\-–—]\s*\$?([\d,]+[\dkKmMbB]?)',
            re.IGNORECASE
        )

        for match in pattern.finditer(text):
            severity = match.group(1).lower().capitalize()
            amount_str = match.group(2)
            # Parse amount with k/m suffixes
            amount_str = amount_str.replace(",", "").lower()
            if amount_str.endswith("k"):
                amount = float(amount_str[:-1]) * 1000
            elif amount_str.endswith("m"):
                amount = float(amount_str[:-1]) * 1000000
            else:
                try:
                    amount = float(amount_str)
                except ValueError:
                    continue
            rewards[severity] = int(amount)

        return rewards

    @staticmethod
    def check_pays_for_medium(reward_table: dict) -> bool:
        """Check if reward table includes Medium severity payments."""
        return "Medium" in reward_table and reward_table["Medium"] > 0