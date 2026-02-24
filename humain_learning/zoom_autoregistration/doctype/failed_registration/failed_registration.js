// Copyright (c) 2026, Raghav Kaul and contributors
// For license information, please see license.txt

frappe.ui.form.on("Failed Registration", {
    retry_registration(frm) {
        frappe.call({
            method: "humain_learning.zoom_autoregistration.lead_hooks.retry_failed_registration",
            args: {
                lead: frm.doc.lead,
                webinar: frm.doc.webinar
            },
            freeze: true,
            freeze_message: "Retrying registration..."
        }).then(() => {
            frappe.msgprint("Retry job queued.");
            frm.reload_doc();
        });

    }
});