// Copyright (c) 2026, Raghav Kaul and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bolna Call", {
	refresh(frm) {
		const url = frm.doc.recording_url;

		if (!url) {
			frm.set_df_property("play_audio", "options", "");
			return;
		}

		frm.set_df_property(
			"play_audio",
			"options",
			`<audio controls preload="none" style="width: 100%;">
				<source src="${url}">
				Your browser does not support the audio element.
			</audio>`
		);

		frm.add_custom_button(__("Process Extrations"), function() {
			if (!frm.doc.extracted_data) {
				frappe.throw("No extractions found.");
				return;
			};
			if(!frm.doc.extractions_processed) {
				frappe.call({
				method: "humain_learning.bolna.services.process_extractions",
				args: {
					call_doc: frm.doc.name
				},
				callback: function(r) {
					if (!r.exc) {
						frappe.msgprint("Extractions processed and lead updated.")
					}
				}
			})
			}
			else {
				frappe.throw("Extractions already processed.")
			}
			
		});
	}
});