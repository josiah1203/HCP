from __future__ import annotations

"""Minimal S-expression parser for KiCad board/schematic files."""


def parse_sexpr(text: str) -> list | str | int | float:
    tokens = _tokenize(text)
    tree, _ = _parse_tokens(tokens, 0)
    return tree


def _tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in " \t\n\r":
            i += 1
            continue
        if ch == "(":
            tokens.append("(")
            i += 1
            continue
        if ch == ")":
            tokens.append(")")
            i += 1
            continue
        if ch == '"':
            j = i + 1
            parts: list[str] = []
            while j < n:
                if text[j] == "\\" and j + 1 < n:
                    parts.append(text[j + 1])
                    j += 2
                    continue
                if text[j] == '"':
                    break
                parts.append(text[j])
                j += 1
            tokens.append("".join(parts))
            i = j + 1
            continue
        j = i
        while j < n and text[j] not in " \t\n\r()":
            j += 1
        tokens.append(text[i:j])
        i = j
    return tokens


def _parse_tokens(
    tokens: list[str], index: int
) -> tuple[list | str | int | float, int]:
    if index >= len(tokens):
        return [], index
    token = tokens[index]
    if token != "(":
        return _parse_atom(token), index + 1
    index += 1
    items: list = []
    while index < len(tokens) and tokens[index] != ")":
        item, index = _parse_tokens(tokens, index)
        items.append(item)
    return items, index + 1 if index < len(tokens) else index


def _parse_atom(token: str) -> str | int | float:
    if token in ("yes", "no"):
        return token
    try:
        if "." in token or "e" in token.lower():
            return float(token)
        return int(token)
    except ValueError:
        return token


def sexpr_find(node: list | str | int | float, head: str) -> list:
    """Return all sublists whose first element equals head."""
    if not isinstance(node, list):
        return []
    found: list = []
    if node and node[0] == head:
        found.append(node)
    for child in node:
        if isinstance(child, list):
            found.extend(sexpr_find(child, head))
    return found


def sexpr_child(node: list, head: str) -> list | None:
    for item in node:
        if isinstance(item, list) and item and item[0] == head:
            return item
    return None
