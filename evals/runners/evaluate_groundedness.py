
import json
import argparse
from pathlib import Path


def evaluate_case(case):
    answer = case.get("answer") or ""
    passages = case.get("passages") or []
    category = case.get("category")

    evidence = [
        p for p in passages
        if p.get("content", "").strip()
        and not p.get("content", "").startswith(
            "Error invoking tool"
        )
    ]

    result = {
        "id": case["id"],
        "category": category,
        "sources": sorted({
            p.get("source", "unknown")
            for p in evidence
        }),
        "passage_count": len(evidence),
        "answer_present": bool(answer.strip()),
        "review_required": True,
    }

    if case.get("error"):
        result["status"] = "execution_error"
    elif not answer.strip():
        result["status"] = "missing_answer"
    elif category == "groundedness" and not evidence:
        result["status"] = "missing_evidence"
    elif category == "hallucination":
        result["status"] = "check_abstention"
    else:
        result["status"] = "check_claim_support"

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    path = Path(args.report)

    with path.open(encoding="utf-8") as f:
        report = json.load(f)

    results = [
        evaluate_case(case)
        for case in report["results"]
    ]

    output = path.with_name(
        path.stem + "_groundedness_review.json"
    )

    output.write_text(
        json.dumps(
            {
                "source_report": str(path),
                "results": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    for result in results:
        print(
            result["id"],
            "|",
            result["status"],
            "| Passages:",
            result["passage_count"],
        )

    print("\nReview report:", output)


if __name__ == "__main__":
    main()