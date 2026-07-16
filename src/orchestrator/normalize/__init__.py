"""
Finding normalizer — validates and normalizes tool adapter outputs against shared schema.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import jsonschema


class SchemaValidationError(Exception):
    """Raised when a finding record fails schema validation."""
    pass


class FindingNormalizer:
    """Validates and normalizes tool findings against the shared finding schema."""

    SCHEMA_VERSION = "1.0.0"
    
    # Required fields that every normalized finding must have
    REQUIRED_FIELDS = [
        "finding_id", "classification", "tool", "location",
        "title", "description", "provenance", "schema_version"
    ]

    def __init__(self, schema_path: Optional[str] = None):
        self.schema_path = schema_path
        self.schema = None
        if schema_path and Path(schema_path).exists():
            try:
                self.schema = json.loads(Path(schema_path).read_text())
            except Exception:
                pass

    def validate(self, finding: dict) -> list[str]:
        """Validate a finding record against the JSON Schema and required fields. Returns list of errors."""
        errors = []

        # JSON Schema validation (when schema is loaded)
        if self.schema is not None:
            try:
                jsonschema.validate(finding, self.schema)
            except jsonschema.ValidationError as e:
                errors.append(f"Schema validation error: {e.message}")
                return errors  # Early return — schema is authoritative

        for field in self.REQUIRED_FIELDS:
            if field not in finding:
                errors.append(f"Missing required field: {field}")
        
        # Validate classification
        valid_classes = [
            "confirmed_vulnerability", "reproducible_suspicious_behavior",
            "invariant_violation", "tool_generated_warning", "duplicate_finding",
            "informational_observation", "unsupported_hypothesis", "false_positive",
            "analysis_failure"
        ]
        if "classification" in finding and finding["classification"] not in valid_classes:
            errors.append(f"Invalid classification: {finding.get('classification')}")
        
        # Validate severity
        valid_severities = ["critical", "high", "medium", "low", "informational", "none"]
        if "severity" in finding and finding.get("severity") not in valid_severities:
            errors.append(f"Invalid severity: {finding.get('severity')}")
        
        # Validate tool info
        tool = finding.get("tool", {})
        if not isinstance(tool, dict):
            errors.append("Tool info must be a dict")
        elif "name" not in tool:
            errors.append("Missing tool.name")
        
        # Validate location
        location = finding.get("location", {})
        if not isinstance(location, dict):
            errors.append("Location info must be a dict")
        elif "file" not in location:
            errors.append("Missing location.file")
        
        return errors

    def normalize(self, raw_findings: list[dict], job_id: str, 
                  tool_name: str, tool_version: str, adapter_version: str,
                  target_commit: str = "") -> tuple[list[dict], list[dict]]:
        """
        Normalize raw tool findings into validated schema records.
        
        Returns: (valid_findings, quarantined_findings)
        """
        valid = []
        quarantined = []
        
        for i, raw in enumerate(raw_findings):
            # Ensure required fields
            finding = dict(raw)
            
            # Add finding_id if missing
            if "finding_id" not in finding:
                finding["finding_id"] = str(uuid.uuid4())
            
            # Add job_id
            finding["job_id"] = job_id
            
            # Ensure tool info
            if "tool" not in finding:
                finding["tool"] = {"name": tool_name, "version": tool_version, "rule_id": f"unknown-{i}"}
            else:
                finding["tool"].setdefault("version", tool_version)
                finding["tool"].setdefault("name", tool_name)
            
            # Ensure location
            if "location" not in finding:
                finding["location"] = {"file": "", "start_line": 0, "end_line": 0}
            
            # Ensure provenance
            if "provenance" not in finding:
                finding["provenance"] = {
                    "job_id": job_id,
                    "target_commit": target_commit,
                    "adapter_version": adapter_version,
                    "schema_version": self.SCHEMA_VERSION,
                }
            else:
                finding["provenance"].setdefault("job_id", job_id)
                finding["provenance"].setdefault("adapter_version", adapter_version)
                finding["provenance"].setdefault("schema_version", self.SCHEMA_VERSION)
            
            # Ensure timestamps
            if "timestamps" not in finding:
                finding["timestamps"] = {
                    "normalized": datetime.now(timezone.utc).isoformat(),
                }
            
            # Ensure deduplication_group
            if "deduplication_group" not in finding:
                finding["deduplication_group"] = finding["finding_id"]
            
            # Ensure reproduction status
            if "reproduction" not in finding:
                finding["reproduction"] = {"status": "none"}
            
            # Set schema version
            finding["schema_version"] = self.SCHEMA_VERSION
            
            # Validate
            errors = self.validate(finding)
            if errors:
                finding["validation_errors"] = errors
                finding["classification"] = "analysis_failure"
                quarantined.append(finding)
            else:
                valid.append(finding)
        
        return valid, quarantined


class Deduplicator:
    """Deterministic finding deduplication engine."""

    def __init__(self):
        self.criteria_weights = {
            "file_line": 1.0,      # Same file + same line range
            "detector_rule": 0.9,  # Same detector/rule ID
            "contract": 0.8,       # Same contract
            "vuln_category": 0.7,  # Same vulnerability category
            "call_path": 0.6,      # Similar call path
        }

    def dedup(self, findings: list[dict]) -> list[dict]:
        """
        Deterministic deduplication of findings.
        Returns findings with deduplication_group populated.
        """
        groups = {}
        
        for finding in findings:
            # Build dedup key from available evidence
            key_parts = []
            
            # Source location is strongest signal
            loc = finding.get("location", {})
            if loc.get("file"):
                key_parts.append(f"file:{loc['file']}")
            if loc.get("start_line"):
                key_parts.append(f"line:{loc['start_line']}")
            
            # Detector/rule ID
            tool = finding.get("tool", {})
            if tool.get("rule_id"):
                key_parts.append(f"rule:{tool['rule_id']}")
            
            # Contract name
            if loc.get("contract"):
                key_parts.append(f"contract:{loc['contract']}")
            
            # Vulnerability category
            cat = finding.get("vulnerability_category")
            if cat:
                key_parts.append(f"cat:{cat}")
            
            # Build group key
            if key_parts:
                group_key = "|".join(key_parts)
            else:
                group_key = finding.get("finding_id", "unknown")
            
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(finding)
        
        # Assign group IDs and determine primary findings
        deduped = []
        for group_key, group_findings in groups.items():
            if len(group_findings) == 1:
                # Single finding — no duplication
                deduped.append(group_findings[0])
            else:
                # Multiple findings — mark as duplicates
                # Keep the strongest (highest severity) as primary
                severity_order = {"critical": 5, "high": 4, "medium": 3, "low": 2, "informational": 1, "none": 0}
                sorted_findings = sorted(
                    group_findings,
                    key=lambda f: severity_order.get(f.get("severity", "none"), 0),
                    reverse=True,
                )
                
                for i, finding in enumerate(sorted_findings):
                    finding["deduplication_group"] = group_key
                    if i > 0:
                        # Mark as duplicate, preserve original as evidence
                        finding["classification"] = "duplicate_finding"
                    deduped.append(finding)
        
        return deduped