import frappe
from frappe.model.document import Document


class JobReview(Document):
    """Lower-level PHILharmonicFlows object. Lifecycle advance + macro propagation
    are handled centrally by the engine adapter via doc_events (see hooks.py),
    so the controller stays thin."""
    pass
