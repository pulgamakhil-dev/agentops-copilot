
"""
Evaluate Supervisor routing against a versioned test dataset.

This runner only calls Supervisor.route(). It never invokes
operational agents or executes pipeline actions.
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from app.agents.supervisor import SupervisorAgent


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DATASET = (
    PROJECT_ROOT / "evals" / "datasets" / "routing_cases.json"
)
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "evals" / "results"

VALID_AGENTS = {
    "monitoring",
    "sql",
    "rag",
    "investigation",
    "action",
}


def load_dataset(dataset_path: Path) -> list[dict]:
    """Load and validate routing evaluation cases."""

    with dataset_path.open("r", encoding="utf-8") as file:
        cases = json.load(file)

    if not isinstance(cases, list) or not cases:
        raise ValueError("Evaluation dataset must be a non-empty list.")

    seen_ids = set()

    for case in cases:
        required = {"id", "query", "expected_agent"}

        if not isinstance(case, dict) or not required.issubset(case):
            raise ValueError(f"Invalid evaluation case: {case}")

        if not all(
            isinstance(case[field], str) and case[field].strip()
            for field in required
        ):
            raise ValueError(f"Empty or invalid fields: {case}")

        if case["id"] in seen_ids:
            raise ValueError(f"Duplicate case ID: {case['id']}")

        seen_ids.add(case["id"])

        if case["expected_agent"] not in VALID_AGENTS:
            raise ValueError(
                f"Invalid expected agent in {case['id']}: "
                f"{case['expected_agent']}"
            )

    return cases


def evaluate(
    dataset_path: Path,
    results_dir: Path,
) -> dict:
    """Run each case through the real Supervisor routing model."""

    cases = load_dataset(dataset_path)
    supervisor = SupervisorAgent()

    results = []
    correct = 0

    for index, case in enumerate(cases, start=1):
        print(
            f"\n[{index}/{len(cases)}] "
            f"{case['id']}: {case['query']}",
            flush=True,
        )

        start = time.perf_counter()
        actual_agent = None
        error = None
        reason = None

        try:
            decision = supervisor.route(case["query"])
            actual_agent = decision.agent
            reason = decision.reason

        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

        latency_seconds = round(
            time.perf_counter() - start,
            3,
        )

        passed = (
            error is None
            and actual_agent == case["expected_agent"]
        )

        if passed:
            correct += 1

        result = {
            "id": case["id"],
            "query": case["query"],
            "category": case.get("category", "uncategorized"),
            "expected_agent": case["expected_agent"],
            "actual_agent": actual_agent,
            "passed": passed,
            "reason": reason,
            "latency_seconds": latency_seconds,
            "error": error,
        }

        results.append(result)

        print(
            f"Expected: {case['expected_agent']} | "
            f"Actual: {actual_agent} | "
            f"{'PASS' if passed else 'FAIL'} | "
            f"{latency_seconds}s",
            flush=True,
        )

        if error:
            print(f"Error: {error}", flush=True)

    total = len(cases)
    accuracy = round(correct / total * 100, 2)

    report = {
        "evaluation": "supervisor_routing",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": str(dataset_path),
        "total": total,
        "passed": correct,
        "failed": total - correct,
        "accuracy_percent": accuracy,
        "results": results,
    }

    results_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%d_%H%M%S"
    )

    output_path = (
        results_dir / f"routing_evaluation_{timestamp}.json"
    )

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    print("\n========== EVALUATION SUMMARY ==========")
    print(f"Total cases: {total}")
    print(f"Passed: {correct}")
    print(f"Failed: {total - correct}")
    print(f"Routing accuracy: {accuracy}%")
    print(f"Report: {output_path}")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate AgentOps Supervisor routing."
    )

    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
    )

    args = parser.parse_args()

    evaluate(
        dataset_path=args.dataset,
        results_dir=args.results_dir,
    )


if __name__ == "__main__":
    main()