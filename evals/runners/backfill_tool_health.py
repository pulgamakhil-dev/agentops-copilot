
import json
from pathlib import Path

from evals.runners.evaluate_rag import check_tool_health

report_path = Path(
    "evals/results/rag_evaluation_20260922_183529.json"
)

with report_path.open(encoding="utf-8") as file:
    report = json.load(file)

for result in report["results"]:
    # The existing report contains tool calls and parsed passages.
    # Parsed passages alone cannot reliably reveal every tool error.
    health = check_tool_health(
        result.get("tool_calls", []),
        result.get("passages", []),
    )

    result["tool_health"] = health

    print(
        result["id"],
        "| Valid arguments:",
        health["valid_arguments"],
        "| Tool errors detected:",
        len(health["tool_errors"]),
    )

output = report_path.with_name(
    report_path.stem + "_with_tool_health.json"
)

with output.open("w", encoding="utf-8") as file:
    json.dump(report, file, indent=2)

print("Updated report:", output)