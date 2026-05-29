app_name = "philharmonic"
app_title = "PHILharmonicFlows"
app_publisher = "PHILharmonicFlows scaffold"
app_description = "Object-aware (object-centric) process management on Frappe DocTypes"
app_email = "noreply@example.com"
app_license = "MIT"
app_version = "0.1.0"

# -----------------------------------------------------------------------------
# Document Events -> PHILharmonicFlows engine
#
#   validate   : advance the object's own lifecycle (micro process) from its data
#                BEFORE the row is written, so persisted `state` is always
#                consistent with attribute values (data-driven execution).
#   on_update  : propagate to higher-level objects (macro coordination) -- a
#                review reaching `submitted` may unblock its parent application.
# -----------------------------------------------------------------------------
doc_events = {
    "Job Application": {
        "validate": "philharmonic.philharmonic.engine.adapter.evaluate_doc",
        "on_update": "philharmonic.philharmonic.engine.adapter.propagate",
    },
    "Job Review": {
        "validate": "philharmonic.philharmonic.engine.adapter.evaluate_doc",
        "on_update": "philharmonic.philharmonic.engine.adapter.propagate",
    },
}

# Client script: adds the "Pending Activity" indicator + form-based activity
# affordance inside Desk forms (the form-js role is played by Desk's own form,
# driven by the pending_activities whitelisted method).
doctype_js = {
    "Job Application": "public/js/pf_form.js",
    "Job Review": "public/js/pf_form.js",
}

# Optional seed data for a quick demo (`bench --site <site> execute
# philharmonic.philharmonic.install.seed_demo`). Not auto-run on install.
