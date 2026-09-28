
from evals.runners.judge_groundedness import (
    GroundednessJudgment,
    validate_judgment,
)


def make_judgment(**overrides):
    values = {
        "retrieval_relevant": False,
        "answer_grounded": True,
        "answer_complete": True,
        "appropriate_abstention": True,
        "unsupported_claims": [],
        "missing_information": [],
        "explanation": (
            "The answer correctly acknowledges that "
            "the requested information is unavailable."
        ),
    }
    values.update(overrides)
    return GroundednessJudgment(**values)


def test_correct_abstention_has_no_warnings():
    judgment = make_judgment()

    warnings = validate_judgment(
        judgment,
        answer="The runbook does not contain the password.",
    )

    assert warnings == []


def test_reversed_negation_is_detected():
    judgment = make_judgment(
        answer_grounded=False,
        unsupported_claims=[
            "The runbook contains the password."
        ],
    )

    warnings = validate_judgment(
        judgment,
        answer="The runbook does not contain the password.",
    )

    assert any(
        "not present in the answer" in warning
        for warning in warnings
    )


def test_contradictory_abstention_is_flagged():
    judgment = make_judgment(
        answer_grounded=False,
    )

    warnings = validate_judgment(
        judgment,
        answer="Mars deployment is not documented.",
    )

    assert any(
        "despite appropriate abstention" in warning
        for warning in warnings
    )


def test_incomplete_answer_can_be_grounded():
    judgment = make_judgment(
        answer_grounded=True,
        answer_complete=False,
        appropriate_abstention=False,
        missing_information=[
            "Documented remediation steps"
        ],
    )

    warnings = validate_judgment(
        judgment,
        answer="Check the pipeline error logs.",
    )

    assert warnings == []