// Copyright (c) 2026, Raghav Kaul and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Bolna Phone", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on("Bolna Phone", {
    refresh(frm) {
        frm.add_custom_button("Fetch Phone", () => {
            frappe.call({
                method: "humain_learning.bolna.services.sync_bolna_phone",
                freeze: true,
                freeze_message: "Syncing Bolna Phone"
            }).then((r) => {
                frm.reload_doc();
            });
        });
    }
});