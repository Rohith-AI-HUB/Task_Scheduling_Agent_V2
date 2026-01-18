from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MadeGroup:
    member_uids: list[str]
    assigned_problem_index: Optional[int]
    assigned_problem_statement: Optional[str]


def make_groups(
    *,
    student_uids: list[str],
    group_size: int,
    problem_statements: Optional[list[str]] = None,
    seed: Optional[int] = None,
) -> list[MadeGroup]:
    if group_size < 2:
        raise ValueError("group_size must be at least 2")

    roster = [u for u in student_uids if isinstance(u, str) and u.strip()]
    if not roster:
        return []

    rng = random.Random(seed)
    rng.shuffle(roster)

    full_group_count = len(roster) // group_size
    remainder = len(roster) % group_size

    groups: list[list[str]] = []
    idx = 0
    for _ in range(full_group_count):
        groups.append(roster[idx : idx + group_size])
        idx += group_size

    if remainder:
        leftover = roster[idx:]
        if not groups:
            groups.append(leftover)
        else:
            for i, uid in enumerate(leftover):
                groups[i % len(groups)].append(uid)

    normalized_problems = [
        s.strip()
        for s in (problem_statements or [])
        if isinstance(s, str) and s.strip()
    ]

    made: list[MadeGroup] = []
    for i, members in enumerate(groups):
        problem_idx: Optional[int] = None
        problem_text: Optional[str] = None
        if normalized_problems:
            problem_idx = i % len(normalized_problems)
            problem_text = normalized_problems[problem_idx]
        made.append(
            MadeGroup(
                member_uids=list(members),
                assigned_problem_index=problem_idx,
                assigned_problem_statement=problem_text,
            )
        )
    return made
