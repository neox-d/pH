"""
Registry of PHILharmonicFlows object models, keyed by DocType name.

Mirrors `PhilFlows.Examples.Recruitment` from the Elixir implementation:

  * Job Review  (lower-level):  initiated -> filled -> submitted
  * Job Application (higher-level): submitted -> reviewing -> {rejected | decided -> hired}
    with a MACRO rule blocking reviewing->decided until ALL related reviews are submitted.

In a production app these would be rows in the "PF Object Config" DocType, edited
in Desk. They are defined in code here so the engine has a single source of truth
that is identical to the Elixir/JS versions and unit-testable.
"""
from __future__ import annotations
from typing import Dict

from .lifecycle import ObjectModel, State, Transition, Coordination


def job_review() -> ObjectModel:
    return ObjectModel(
        name="Job Review",
        initial_state="initiated",
        states=[
            State("initiated"),
            State(
                "filled",
                condition=[
                    "or",
                    [
                        ["eq", "proposal", "reject"],
                        ["and", [["eq", "proposal", "invite"], ["set", "appraisal"]]],
                    ],
                ],
            ),
            State("submitted", condition=["set", "proposal"], terminal=True),
        ],
        transitions=[
            Transition("initiated", "filled", guard=["set", "proposal"]),
            Transition("filled", "submitted", guard=["set", "proposal"]),
        ],
    )


def job_application() -> ObjectModel:
    return ObjectModel(
        name="Job Application",
        initial_state="submitted",
        states=[
            State("submitted"),
            State("reviewing", condition=["eq", "eligible", 1]),
            State("rejected", condition=["eq", "eligible", 0], terminal=True),
            State("decided", condition=["set", "decision"]),
            State("hired", condition=["eq", "decision", "accept"], terminal=True),
        ],
        transitions=[
            Transition("submitted", "reviewing", guard=["eq", "eligible", 1]),
            Transition("submitted", "rejected", guard=["eq", "eligible", 0]),
            Transition("reviewing", "decided", guard=["set", "decision"]),
            Transition("decided", "hired", guard=["eq", "decision", "accept"]),
        ],
        coordinations=[
            Coordination(
                from_state="reviewing",
                to_state="decided",
                kind="all",
                relation="reviews",
                child_state="submitted",
            )
        ],
    )


_REGISTRY = {
    "Job Review": job_review,
    "Job Application": job_application,
}


def get_model(doctype: str) -> ObjectModel:
    if doctype not in _REGISTRY:
        raise KeyError(f"no PHILharmonicFlows model registered for DocType {doctype!r}")
    return _REGISTRY[doctype]()


def is_managed(doctype: str) -> bool:
    return doctype in _REGISTRY
