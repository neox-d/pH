import frappe
from frappe.model.document import Document


class JobApplication(Document):
    """Higher-level PHILharmonicFlows object. Owns Job Reviews through the
    `reviews` child table. Lifecycle + coordination handled by the engine
    adapter via doc_events (see hooks.py)."""
    pass
