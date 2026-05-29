"""
PHILharmonicFlows micro-process engine (object lifecycle), pure-Python core.

The Frappe layer adapts a real DocType + its PF Object Config into the light
`ObjectModel` structure below, runs `advance`, and writes the resulting state
back to the doc. Keeping the algorithm here (no `frappe` import) means the
genuinely tricky part -- data-driven chaining + coordination gating -- is
unit-tested directly.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .condition import evaluate, referenced_attrs


@dataclass
class State:
    name: str
    condition: Any = None          # data condition; None == always
    terminal: bool = False


@dataclass
class Transition:
    from_state: str
    to_state: str
    guard: Any = None              # data condition over attrs


@dataclass
class Coordination:
    # transition (from,to) of THIS object is gated on related instances
    from_state: str
    to_state: str
    kind: str                      # "all" | "any" | "count_gte"
    relation: str                  # name of the child/link relation
    child_state: Optional[str] = None
    child_condition: Any = None
    count: int = 1


@dataclass
class ObjectModel:
    name: str
    initial_state: str
    states: List[State] = field(default_factory=list)
    transitions: List[Transition] = field(default_factory=list)
    coordinations: List[Coordination] = field(default_factory=list)

    def state(self, name: str) -> Optional[State]:
        return next((s for s in self.states if s.name == name), None)

    def transitions_from(self, name: str) -> List[Transition]:
        return [t for t in self.transitions if t.from_state == name]


# A "relation resolver" returns the list of related child instances for a given
# (parent_attrs, relation_name). Each child is represented as a dict with at
# least {"state": ..., **attrs}. The Frappe layer supplies a resolver backed by
# child tables / Link queries; tests supply an in-memory one.
RelationResolver = Callable[[Dict[str, Any], str], List[Dict[str, Any]]]


def coordination_allows(
    model: ObjectModel,
    transition: Transition,
    attrs: Dict[str, Any],
    resolve: RelationResolver,
) -> bool:
    """Macro-level gate: do all coordination rules for this transition hold?"""
    rules = [
        c for c in model.coordinations
        if c.from_state == transition.from_state and c.to_state == transition.to_state
    ]
    return all(_rule_holds(c, attrs, resolve) for c in rules)


def _child_matches(child: Dict[str, Any], rule: Coordination) -> bool:
    if rule.child_state is not None:
        return child.get("state") == rule.child_state
    return evaluate(rule.child_condition, child)


def _rule_holds(rule: Coordination, attrs: Dict[str, Any], resolve: RelationResolver) -> bool:
    children = resolve(attrs, rule.relation)
    if rule.kind == "all":
        return len(children) > 0 and all(_child_matches(c, rule) for c in children)
    if rule.kind == "any":
        return any(_child_matches(c, rule) for c in children)
    if rule.kind == "count_gte":
        return sum(1 for c in children if _child_matches(c, rule)) >= rule.count
    return True


def enabled_transition(
    model: ObjectModel,
    state_name: str,
    attrs: Dict[str, Any],
    resolve: RelationResolver,
) -> Optional[Transition]:
    """First transition out of `state_name` whose guard + target condition + macro
    gate all hold."""
    for tr in model.transitions_from(state_name):
        target = model.state(tr.to_state)
        if target is None:
            continue
        if (
            evaluate(tr.guard, attrs)
            and evaluate(target.condition, attrs)
            and coordination_allows(model, tr, attrs, resolve)
        ):
            return tr
    return None


def advance(
    model: ObjectModel,
    state_name: str,
    attrs: Dict[str, Any],
    resolve: RelationResolver,
) -> Tuple[str, List[str]]:
    """Data-driven advance: keep firing enabled transitions until none is enabled.
    Returns (new_state, list_of_states_entered_this_call)."""
    entered: List[str] = []
    current = state_name
    guard_limit = len(model.states) + 1  # prevent pathological cycles
    while guard_limit > 0:
        guard_limit -= 1
        tr = enabled_transition(model, current, attrs, resolve)
        if tr is None:
            break
        current = tr.to_state
        entered.append(current)
    return current, entered


def pending_attributes(model: ObjectModel, state_name: str, attrs: Dict[str, Any]) -> List[str]:
    """Mandatory-but-unset attributes referenced by guards out of the current
    state -- i.e. the dynamically generated form-based activity."""
    needed: List[str] = []
    for tr in model.transitions_from(state_name):
        for a in referenced_attrs(tr.guard):
            if attrs.get(a) in (None, "") and a not in needed:
                needed.append(a)
    return needed
