from __future__ import annotations

from parser.parsers.sexpr import parse_sexpr, sexpr_find


def test_parse_nested():
    tree = parse_sexpr('(a 1 (b "hello"))')
    assert tree == ["a", 1, ["b", "hello"]]


def test_sexpr_find():
    tree = parse_sexpr("(root (net 1) (net 2))")
    assert len(sexpr_find(tree, "net")) == 2
