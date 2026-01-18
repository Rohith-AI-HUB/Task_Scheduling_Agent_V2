from __future__ import annotations

import pytest

from app.ai.group_maker import make_groups


def test_make_groups_balanced_when_divisible():
    students = [f"s{i}" for i in range(12)]
    groups = make_groups(student_uids=students, group_size=3, seed=1)
    assert len(groups) == 4
    assert sorted(len(g.member_uids) for g in groups) == [3, 3, 3, 3]


def test_make_groups_distributes_remainder():
    students = [f"s{i}" for i in range(10)]
    groups = make_groups(student_uids=students, group_size=3, seed=2)
    assert len(groups) == 3
    assert sorted(len(g.member_uids) for g in groups) == [3, 3, 4]
    all_members = [u for g in groups for u in g.member_uids]
    assert sorted(all_members) == sorted(students)


def test_make_groups_single_group_when_smaller_than_group_size():
    students = ["a", "b", "c"]
    groups = make_groups(student_uids=students, group_size=5, seed=3)
    assert len(groups) == 1
    assert sorted(groups[0].member_uids) == sorted(students)


def test_make_groups_assigns_problems_round_robin():
    students = [f"s{i}" for i in range(14)]
    problems = ["P1", "P2"]
    groups = make_groups(student_uids=students, group_size=3, problem_statements=problems, seed=4)
    assert len(groups) == 4
    assert [g.assigned_problem_index for g in groups] == [0, 1, 0, 1]
    assert [g.assigned_problem_statement for g in groups] == ["P1", "P2", "P1", "P2"]


def test_make_groups_is_deterministic_with_seed():
    students = [f"s{i}" for i in range(11)]
    g1 = make_groups(student_uids=students, group_size=3, seed=123)
    g2 = make_groups(student_uids=students, group_size=3, seed=123)
    assert [x.member_uids for x in g1] == [x.member_uids for x in g2]


def test_make_groups_rejects_invalid_group_size():
    with pytest.raises(ValueError):
        make_groups(student_uids=["a", "b"], group_size=1)

