from __future__ import annotations

LIFECYCLE_TRANSITIONS: dict[tuple[str, str], tuple[str, str]] = {
    ("draft", "in_review"): ("editor", "lifecycle_submit"),
    ("in_review", "draft"): ("approver", "lifecycle_reject"),
    ("in_review", "approved"): ("approver", "lifecycle_approve"),
    ("approved", "released"): ("approver", "lifecycle_release"),
    ("released", "obsolete"): ("admin", "lifecycle_obsolete"),
}


def validate_transition(from_state: str, to_state: str) -> tuple[str, str] | None:
    return LIFECYCLE_TRANSITIONS.get((from_state, to_state))
