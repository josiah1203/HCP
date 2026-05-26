from __future__ import annotations

ROLE_RANK = {"viewer": 0, "editor": 1, "approver": 2, "admin": 3}


def role_at_least(role: str, minimum: str) -> bool:
    return ROLE_RANK.get(role, -1) >= ROLE_RANK.get(minimum, 99)


def can_upload(role: str) -> bool:
    return role_at_least(role, "editor")


def can_approve(role: str) -> bool:
    return role_at_least(role, "approver")


def can_admin(role: str) -> bool:
    return role_at_least(role, "admin")
