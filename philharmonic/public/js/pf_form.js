// PHILharmonicFlows Desk integration.
//
// Inside the standard Desk form (the data-oriented + process-oriented view), this:
//   * shows the current lifecycle state as a colored indicator,
//   * fetches the dynamically-generated "pending activity" (mandatory-but-unset
//     attributes blocking progress) and highlights those fields,
//   * surfaces a dashboard comment so the user knows what to fill to advance.
//
// The lifecycle itself advances server-side on save (doc_events -> engine), so
// this script is purely the front-of-house; saving re-evaluates and the state
// field (read-only) updates on reload.

frappe.ui.form.on("Job Application", {
  refresh: pf_refresh,
});

frappe.ui.form.on("Job Review", {
  refresh: pf_refresh,
});

function pf_refresh(frm) {
  if (frm.is_new()) return;
  pf_show_state(frm);
  pf_show_pending(frm);
}

function pf_show_state(frm) {
  const state = frm.doc.state || "—";
  const terminal = ["submitted", "hired", "rejected"].includes(state);
  const color = terminal ? "green" : "blue";
  frm.dashboard.clear_headline();
  frm.dashboard.set_headline(
    `<span class="indicator ${color}">Lifecycle state: <b>${frappe.utils.escape_html(state)}</b></span>`
  );
}

function pf_show_pending(frm) {
  frappe.call({
    method: "philharmonic.philharmonic.engine.adapter.pending_activities",
    args: { doctype: frm.doctype, name: frm.docname },
    callback: function (r) {
      if (!r.message) return;
      const pending = r.message.pending || [];

      // clear previous highlights
      (frm._pf_highlighted || []).forEach((f) => {
        const w = frm.get_field(f);
        if (w && w.$wrapper) w.$wrapper.css("box-shadow", "");
      });
      frm._pf_highlighted = [];

      if (pending.length === 0) {
        frm.dashboard.add_comment(
          __("No pending activity — lifecycle will advance automatically as data allows."),
          "green",
          true
        );
        return;
      }

      const labels = pending.map((p) => p.label).join(", ");
      frm.dashboard.add_comment(
        __("Pending activity — provide: {0}", [labels]),
        "orange",
        true
      );

      // highlight the fields that, once filled, will move the lifecycle forward
      pending.forEach((p) => {
        const w = frm.get_field(p.fieldname);
        if (w && w.$wrapper) {
          w.$wrapper.css("box-shadow", "0 0 0 2px var(--yellow-300, #f1c21b)");
          frm._pf_highlighted.push(p.fieldname);
        }
      });
    },
  });
}
