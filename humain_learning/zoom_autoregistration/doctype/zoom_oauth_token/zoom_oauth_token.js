// Copyright (c) 2026, Raghav Kaul and contributors
// For license information, please see license.txt

frappe.ui.form.on("Zoom OAuth Token", {
	refresh_now(frm) {
        frappe.call({
            method: "humain_learning.zoom_autoregistration.oauth.auth.fetch_and_store_token",
            freeze: true,
            callback(r) {
                if (!r.exc) {
                    frappe.msgprint("Token Refreshed");
                    frm.reload_doc();
                }
            }
        });
	},
});