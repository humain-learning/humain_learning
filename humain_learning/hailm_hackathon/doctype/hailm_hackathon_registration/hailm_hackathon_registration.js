// Copyright (c) 2026, Raghav Kaul and contributors
// For license information, please see license.txt

frappe.ui.form.on("HAILM Hackathon Registration", {
	refresh(frm) {
		const needsRetry =
			frm.doc.status === "Paid" &&
			(frm.doc.code_status !== "Generated" || frm.doc.whatsapp_status !== "Sent");

		if (needsRetry) {
			frm.add_custom_button(__("Retry fulfilment"), () => {
				frappe.call({
					method: "humain_learning.hailm_hackathon.api.retry_fulfilment",
					args: { registration: frm.doc.name },
					freeze: true,
					callback: () => {
						frappe.show_alert({ message: __("Fulfilment queued"), indicator: "blue" });
						setTimeout(() => frm.reload_doc(), 4000);
					},
				});
			});
		}
	},
});
