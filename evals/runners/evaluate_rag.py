
"""
Evaluate the AgentOps Copilot RAG Agent.

Run:
    python -m evals.runners.evaluate_rag

Outputs:
    evals/results/rag_evaluation_<timestamp>.json
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.agents.rag_agent import RAGAgent


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET_PATH = (
    PROJECT_ROOT / "evals" / "datasets" / "rag_cases.json"
)

RESULTS_DIR = PROJECT_ROOT / "evals" / "results"


def load_dataset(path: Path) -> list[dict[str, Any]]:
    """Load the RAG evaluation cases."""

    if not path.exists():
        raise FileNotFoundError(
            f"RAG evaluation dataset not found: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    # Support either a plain list or a dataset object.
    if isinstance(data, list):
        cases = data

    elif isinstance(data, dict):
        cases = data.get("cases", data.get("results", []))

    else:
        raise ValueError(
            "The RAG dataset must contain a list of cases."
        )

    if not isinstance(cases, list):
        raise ValueError(
            "The RAG dataset cases must be a list."
        )

    return cases


def normalize_passages(
    retrieved_evidence: Any,
) -> list[dict[str, str]]:
    """
    Convert agent evidence into evaluation passages.

    The updated RAG Agent returns dictionaries containing:
        content
        source

    Preserve those source values instead of replacing
    them with 'unknown'.
    """

    if not isinstance(retrieved_evidence, list):
        return []

    passages = []

    for item in retrieved_evidence:
        if not isinstance(item, dict):
            continue

        content = item.get("content", "")
        source = item.get("source", "unknown")

        if not isinstance(content, str):
            continue

        if not content.strip():
            continue

        if not isinstance(source, str) or not source.strip():
            source = "unknown"

        passages.append(
            {
                "source": source,
                "content": content,
            }
        )

    return passages


def evaluate_case(
    agent: RAGAgent,
    case: dict[str, Any],
    index: int,
    total: int,
) -> dict[str, Any]:
    """Execute one evaluation case."""

    case_id = case.get("id", f"rag_{index:03d}")
    query = case.get("query", case.get("question", ""))
    category = case.get("category", "unknown")

    print(
        f"\n[{index}/{total}] {case_id}: {query}",
        flush=True,
    )

    start_time = time.perf_counter()

    try:
        if not query:
            raise ValueError(
                f"Missing query for evaluation case {case_id}"
            )

        agent_result = agent.invoke_for_evaluation(query)

        latency = round(
            time.perf_counter() - start_time,
            3,
        )

        passages = normalize_passages(
            agent_result.get("retrieved_evidence", [])
        )

        sources = sorted(
            {
                passage["source"]
                for passage in passages
            }
        )

        tool_calls = agent_result.get("tool_calls", [])

        if not isinstance(tool_calls, list):
            tool_calls = []

        answer = agent_result.get("answer", "")

        retrieval_performed = bool(
            agent_result.get("retrieval_performed", False)
            or passages
        )

        result = {
            "id": case_id,
            "query": query,
            "category": category,
            "answer": answer,
            "retrieval_performed": retrieval_performed,
            "tool_calls": tool_calls,
            "passages": passages,
            "sources": sources,
            "latency_seconds": latency,
            "error": None,
        }

        print(
            f"Retrieved passages: {len(passages)} "
            f"| Sources: {sources} "
            f"| Latency: {latency}s",
            flush=True,
        )

        if not passages:
            print(
                "WARNING: No runbook passages recorded.",
                flush=True,
            )

        return result

    except Exception as exc:
        latency = round(
            time.perf_counter() - start_time,
            3,
        )

        print(
            f"ERROR: {type(exc).__name__}: {exc}",
            flush=True,
        )

        return {
            "id": case_id,
            "query": query,
            "category": category,
            "answer": "",
            "retrieval_performed": False,
            "tool_calls": [],
            "passages": [],
            "sources": [],
            "latency_seconds": latency,
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> None:
    """Run all RAG evaluation cases and save the report."""

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    cases = load_dataset(DATASET_PATH)

    if not cases:
        raise ValueError(
            "The RAG evaluation dataset contains no cases."
        )

    agent = RAGAgent()

    results = []

    total = len(cases)

    for index, case in enumerate(cases, start=1):
        result = evaluate_case(
            agent=agent,
            case=case,
            index=index,
            total=total,
        )

        results.append(result)

    successful = sum(
        1
        for result in results
        if result["error"] is None
    )

    timestamp = datetime.now(timezone.utc)

    report = {
        "evaluation": "rag_evidence_collection",
        "timestamp_utc": timestamp.isoformat(),
        "dataset": str(DATASET_PATH),
        "total": total,
        "successful": successful,
        "results": results,
    }

    filename = (
        "rag_evaluation_"
        f"{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
    )

    report_path = RESULTS_DIR / filename

    with report_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("\n========== RAG EVALUATION ==========")
    print(f"Cases: {total}")
    print(f"Successful calls: {successful}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()