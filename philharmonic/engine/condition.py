"""
PHILharmonicFlows data-condition evaluator.

A "condition" is a small JSON-serializable AST evaluated against a flat dict of
attribute values (a Frappe doc's fields). This is the heart of *data-driven*
execution: a lifecycle state is reached precisely when its condition holds over
the object's attributes -- there is no separate control-flow token.

Kept free of any `frappe` import so it can be unit-tested standalone (and reused
by the client-side mirror). Grammar mirrors the Elixir `PhilFlows.Condition`:

    ["always"]
    ["set", attr]
    ["eq"|"neq"|"gt"|"gte"|"lt"|"lte", attr, value]
    ["in", attr, [values...]]
    ["and", [cond, ...]]
    ["or",  [cond, ...]]
    ["not", cond]
"""
from __future__ import annotations
from typing import Any, Dict, List


class ConditionError(ValueError):
    pass


def evaluate(cond: Any, attrs: Dict[str, Any]) -> bool:
    if cond is None:
        return True
    if not isinstance(cond, list) or not cond:
        raise ConditionError(f"malformed condition: {cond!r}")

    op = cond[0]

    if op == "always":
        return True
    if op == "set":
        return attrs.get(cond[1]) not in (None, "")
    if op == "eq":
        return attrs.get(cond[1]) == cond[2]
    if op == "neq":
        return attrs.get(cond[1]) != cond[2]
    if op == "in":
        return attrs.get(cond[1]) in cond[2]
    if op in ("gt", "gte", "lt", "lte"):
        actual = attrs.get(cond[1])
        if actual is None:
            return False
        return _compare(op, actual, cond[2])
    if op == "and":
        return all(evaluate(c, attrs) for c in cond[1])
    if op == "or":
        return any(evaluate(c, attrs) for c in cond[1])
    if op == "not":
        return not evaluate(cond[1], attrs)

    raise ConditionError(f"unknown operator: {op!r}")


def _compare(op: str, a: Any, b: Any) -> bool:
    if op == "gt":
        return a > b
    if op == "gte":
        return a >= b
    if op == "lt":
        return a < b
    return a <= b


def referenced_attrs(cond: Any) -> List[str]:
    """Attributes a condition reads -- used to compute pending activities."""
    out: List[str] = []
    _collect(cond, out)
    # preserve order, dedupe
    seen = set()
    result = []
    for a in out:
        if a not in seen:
            seen.add(a)
            result.append(a)
    return result


def _collect(cond: Any, out: List[str]) -> None:
    if not isinstance(cond, list) or not cond:
        return
    op = cond[0]
    if op in ("always",):
        return
    if op in ("set",):
        out.append(cond[1])
    elif op in ("eq", "neq", "in", "gt", "gte", "lt", "lte"):
        out.append(cond[1])
    elif op in ("and", "or"):
        for c in cond[1]:
            _collect(c, out)
    elif op == "not":
        _collect(cond[1], out)
