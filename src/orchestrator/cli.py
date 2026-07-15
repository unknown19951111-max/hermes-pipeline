"""
Hermes Pipeline CLI — run the full pipeline from the command line.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from orchestrator.detect import FrameworkDetector
from orchestrator.adapters.base_adapter import ToolAdapter
from orchestrator.adapters.slither_adapter import SlitherAdapter
from orchestrator.adapters.aderyn_adapter import AderynAdapter
from orchestrator.adapters.medusa_adapter import MedusaAdapter
from orchestrator.adapters.echidna_adapter import EchidnaAdapter
from orchestrator.adapters.halmos_adapter import HalmosAdapter
from orchestrator.adapters.hevm_adapter import HevmAdapter
from orchestrator.adapters.wake_adapter import WakeAdapter
from orchestrator.adapters.solana_adapter import AnchorAdapter, SolanaCLIAdapter, TridentAdapter
from orchestrator.adapters.move_adapter import AptosAdapter, SuiAdapter, MoveProverAdapter
from orchestrator.adapters.kontrol_adapter import KontrolAdapter
from orchestrator.adapters.heimdall_adapter import HeimdallAdapter


def cmd_detect(args):
    """Detect ecosystem and framework for a target directory."""
    detector = FrameworkDetector(args.path)
    eco = detector.detect_ecosystem()
    fw = detector.detect_framework()
    result = {
        "ecosystem": eco.to_dict(),
        "framework": fw.to_dict(),
        "path": str(args.path),
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"  Path:       {args.path}")
        print(f"  Ecosystem:  {eco.ecosystem} (confidence: {eco.confidence:.2f})")
        print(f"  Framework:  {fw.framework} (confidence: {fw.confidence:.2f})")
        if eco.evidence:
            print(f"  Evidence:   {eco.evidence[0]}")
        if eco.conflicts:
            print(f"  Conflicts:  {eco.conflicts[0]}")
        if eco.missing:
            print(f"  Missing:    {eco.missing[0]}")
    return 0


def cmd_list_tools(args):
    """List all available tools and their versions."""
    adapters = [
        SlitherAdapter, AderynAdapter, MedusaAdapter, EchidnaAdapter,
        HalmosAdapter, HevmAdapter, WakeAdapter,
        AnchorAdapter, SolanaCLIAdapter, TridentAdapter,
        AptosAdapter, SuiAdapter, MoveProverAdapter,
        KontrolAdapter, HeimdallAdapter,
    ]
    tools = []
    for Adapter in adapters:
        try:
            a = Adapter("/tmp")
            available = a.check_dependencies()
            version = a.get_version() if available else ""
            tools.append({
                "name": Adapter.__name__.replace("Adapter", "").lower(),
                "available": available,
                "version": version,
            })
        except Exception as e:
            tools.append({
                "name": Adapter.__name__.replace("Adapter", "").lower(),
                "available": False,
                "version": f"error: {e}",
            })

    if args.json:
        print(json.dumps(tools, indent=2))
    else:
        print(f"  {'Tool':<20} {'Available':<12} {'Version'}")
        print(f"  {'-'*20} {'-'*12} {'-'*20}")
        for t in tools:
            av = "✅" if t["available"] else "❌"
            print(f"  {t['name']:<20} {av:<12} {t['version']}")
    return 0


def cmd_run(args):
    """Run the pipeline on a target directory."""
    import tempfile
    print(f"  Running Hermes Pipeline on {args.path}...")
    detector = FrameworkDetector(args.path)
    eco = detector.detect_ecosystem()
    fw = detector.detect_framework()
    print(f"  Detected: {eco.ecosystem}/{fw.framework}")

    all_findings = []
    results = {}
    work_dir = tempfile.mkdtemp(prefix="hermes-pipeline-")

    if eco.ecosystem == "evm":
        # Static analysis
        for name, Adapter in [("slither", SlitherAdapter), ("aderyn", AderynAdapter)]:
            a = Adapter(work_dir)
            if a.check_dependencies():
                print(f"  Running {name}...", end=" ", flush=True)
                try:
                    res = a.run(args.path, job_id=f"demo-{name}")
                    findings = res.normalized_findings
                    all_findings.extend(findings)
                    results[name] = {"status": "ok", "findings": len(findings), "version": res.tool_version}
                    print(f"{len(findings)} findings")
                except Exception as e:
                    results[name] = {"status": "error", "error": str(e)}
                    print(f"error: {e}")
            else:
                results[name] = {"status": "skipped"}
                print(f"  Skipping {name} (not available)")

        # Depth-tier
        for name, Adapter in [("halmos", HalmosAdapter), ("wake", WakeAdapter)]:
            a = Adapter(work_dir)
            if a.check_dependencies():
                print(f"  Running {name}...", end=" ", flush=True)
                try:
                    res = a.run(args.path, job_id=f"demo-{name}")
                    findings = res.normalized_findings
                    all_findings.extend(findings)
                    results[name] = {"status": "ok", "findings": len(findings), "version": res.tool_version}
                    print(f"{len(findings)} findings")
                except Exception as e:
                    results[name] = {"status": "error", "error": str(e)}
                    print(f"error: {e}")
            else:
                results[name] = {"status": "skipped"}
                print(f"  Skipping {name} (not available)")

    summary = {
        "path": str(args.path),
        "ecosystem": eco.ecosystem,
        "framework": fw.framework,
        "total_findings": len(all_findings),
        "tool_results": results,
        "findings": all_findings,
    }

    if args.output:
        Path(args.output).write_text(json.dumps(summary, indent=2))
        print(f"\n  Results written to {args.output}")

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"\n  Summary: {len(all_findings)} total findings across {len(results)} tools")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Hermes Pipeline — Smart-Contract Security Auditing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  hermes-pipeline detect /path/to/project
  hermes-pipeline list-tools
  hermes-pipeline run /path/to/project --output results.json
  hermes-pipeline run /path/to/project --json
        """,
    )
    parser.add_argument("--json", action="store_true", help="JSON output")

    sub = parser.add_subparsers(dest="command", required=True)

    # detect
    p_detect = sub.add_parser("detect", help="Detect ecosystem and framework")
    p_detect.add_argument("path", type=str, help="Target project directory")
    p_detect.set_defaults(func=cmd_detect)

    # list-tools
    p_list = sub.add_parser("list-tools", help="List installed tools")
    p_list.set_defaults(func=cmd_list_tools)

    # run
    p_run = sub.add_parser("run", help="Run the full pipeline")
    p_run.add_argument("path", type=str, help="Target project directory")
    p_run.add_argument("--output", "-o", type=str, help="Output JSON file path")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())