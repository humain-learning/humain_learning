// Copyright (c) 2026, Raghav Kaul and contributors
// For license information, please see license.txt

frappe.ui.form.on("Zoom Credentials", {
	connect_to_zoom(frm) {
        frappe.call({
            method: "humain_learning.zoom_autoregistration.oauth.auth.fetch_and_store_token",
            freeze: true,
            callback(r) {
                if (!r.exc) {
                    frappe.msgprint("Connected Successfully");
                    frm.reload_doc();
                }
            }
        });
	},
});
