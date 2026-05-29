"""
Demo seeder. Run after installing the app:

    bench --site <site> execute philharmonic.install.seed_demo

Reproduces the Künzle & Reichert recruitment scenario through the Frappe ORM so
you can watch the lifecycle + macro coordination in Desk.
"""
import frappe


def seed_demo():
    frappe.set_user("Administrator")

    app = frappe.get_doc({
        "doctype": "Job Application",
        "applicant_name": "Ada Lovelace",
    }).insert()
    print(f"Created {app.name}: state={app.state}  (awaiting eligibility)")

    app.eligible = 1
    app.save()
    print(f"Marked eligible -> state={app.state}")

    r1 = frappe.get_doc({"doctype": "Job Review"}).insert()
    r2 = frappe.get_doc({"doctype": "Job Review"}).insert()
    app.append("reviews", {"review": r1.name})
    app.append("reviews", {"review": r2.name})
    app.save()
    print(f"Requested 2 reviews ({r1.name}, {r2.name})")

    app.decision = "accept"
    app.save()
    print(f"Officer decides 'accept' early -> state={app.state}  (macro rule blocks)")

    r1.proposal = "reject"
    r1.save()
    app.reload()
    print(f"{r1.name} submitted -> application state={app.state}  (still blocked, rule is 'all')")

    r2.proposal = "invite"
    r2.appraisal = "Strong candidate"
    r2.save()
    app.reload()
    print(f"{r2.name} submitted -> coordinator unblocks parent -> application state={app.state}")

    frappe.db.commit()
    print("Done. Open the Job Application list in Desk to inspect.")
