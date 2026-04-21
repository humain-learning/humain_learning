// Copyright (c) 2026, Raghav Kaul and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Bolna Phone", {
// 	refresh(frm) {

// 	},
// });
frappe.ui.form.on("Bolna Phone", {
    refresh(frm) {
		frm.add_custom_button("Fetch Phone", () => {
            fetch_and_select_phone(frm);
        });
		frm.add_custom_button("Delete Phone", () => {
			frm.set_value("id", "");
			frm.set_value("phone_no", "");
			frm.set_value("provider", "");
			frm.save();
		})
    }
});

function fetch_and_select_phone(frm ) {
	frappe.call({
		method: "humain_learning.bolna.services.sync_bolna_phone",
		freeze: true,
		freeze_message: "Fetching Bolna Phones",
		callback : function (r) {
			const numbers = r.message || [];

			if (!numbers.length) {
				frappe.throw("No Numbers found on Bolna")
				return;
			}

			const dialogue = new frappe.ui.Dialog({
				title: "Select Number",
				fields: [{
					label: "Available Numbers",
					fieldname: "phone_number",
					fieldtype: "Select",
					options: numbers.map(n => (n.phone_number)),
					reqd: 1
				}],
				primary_action_label: "Select",
				primary_action(values) {
					const chosen = numbers.find(n => n.phone_number === values.phone_number);

					frm.set_value("id", chosen.id);
					frm.set_value("phone_no", chosen.phone_number);
					frm.set_value("provider", chosen.telephony_provider.charAt(0).toUpperCase() + chosen.telephony_provider.slice(1));
					frm.save();
					dialogue.hide();
				}
			});

			dialogue.show();
		}
	});
}