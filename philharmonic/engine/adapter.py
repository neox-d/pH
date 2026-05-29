"""
Frappe <-> engine adapter.

This is the only engine module that imports `frappe`. It:
  * builds an attrs dict from a Frappe doc,
  * supplies a RelationResolver backed by child tables / Link queries,
  * runs the pure `advance`, writes the resulting `state` back, and
  * notifies higher-level (parent) objects so macro coordination propagates.

Wired via `doc_events` in hooks.py (validate / on_update).
"""
from __future__ import annotations
from typing import Any, Dict, List

import frappe

from . import lifecycle
from .registry import get_model, is_managed


# ---- attribute extraction --------------------------------------------------

def doc_attrs(doc) -> Dict[str, Any]:
    """Flat attribute view of a doc the conditions read. `state` excluded; it is
    the lifecycle output, not an input."""
    data = {}
    for df in doc.meta.fields:
        if df.fieldtype in ("Section Break", "Column Break", "Table", "HTML"):
            continue
        if df.fieldname == "state":
            continue
        data[df.fieldname] = doc.get(df.fieldname)
    return data


# ---- relation resolution ---------------------------------------------------

def _resolver_for(doc):
    """Return a RelationResolver closure bound to this doc.

    For the recruitment model the 'reviews' relation is a child table of Job
    Application (rows hold a Link to a Job Review). Each resolved child is a dict
    {state, **attrs} so coordination rules can read child.state.
    """
    def resolve(_attrs: Dict[str, Any], relation: str) -> List[Dict[str, Any]]:
        children = []
        if doc.doctype == "Job Application" and relation == "reviews":
            for row in (doc.get("reviews") or []):
                if not row.review:
                    continue
                child = frappe.get_doc("Job Review", row.review)
                children.append({"state": child.get("state"), **doc_attrs(child)})
        return children

    return resolve


# ---- core entry points (called from doc_events) ----------------------------

def evaluate_doc(doc, method=None):
    """validate hook: advance this object's lifecycle in-memory before save so the
    persisted `state` is always consistent with its data."""
    if not is_managed(doc.doctype):
        return
    model = get_model(doc.doctype)
    if not doc.get("state"):
        doc.state = model.initial_state

    attrs = doc_attrs(doc)
    new_state, _entered = lifecycle.advance(model, doc.state, attrs, _resolver_for(doc))
    doc.state = new_state


def propagate(doc, method=None):
    """on_update hook: a child changed -> re-evaluate higher-level objects that
    relate to it (the macro coordinator's async nudge, done synchronously here)."""
    if not is_managed(doc.doctype):
        return
    if doc.doctype == "Job Review":
        # find parent applications whose child table references this review
        parent_rows = frappe.get_all(
            "Review Link",
            filters={"review": doc.name},
            fields=["parent"],
        )
        for row in parent_rows:
            try:
                parent = frappe.get_doc("Job Application", row.parent)
            except frappe.DoesNotExistError:
                continue
            before = parent.get("state")
            evaluate_doc(parent)
            if parent.get("state") != before:
                parent.save(ignore_permissions=True)


# ---- whitelisted API (consumed by Desk client script / REST) ---------------

@frappe.whitelist()
def pending_activities(doctype: str, name: str):
    """Mandatory-but-unset attributes blocking progress = the form-based activity."""
    doc = frappe.get_doc(doctype, name)
    if not is_managed(doctype):
        return {"pending": []}
    model = get_model(doctype)
    state = doc.get("state") or model.initial_state
    pending = lifecycle.pending_attributes(model, state, doc_attrs(doc))
    fields = []
    for fieldname in pending:
        df = doc.meta.get_field(fieldname)
        fields.append({
            "fieldname": fieldname,
            "label": df.label if df else fieldname,
            "fieldtype": df.fieldtype if df else "Data",
            "options": df.options if df else None,
        })
    return {"state": state, "pending": fields}
