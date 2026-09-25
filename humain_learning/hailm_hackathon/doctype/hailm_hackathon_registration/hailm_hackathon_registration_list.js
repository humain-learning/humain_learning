frappe.listview_settings["HAILM Hackathon Registration"] = {
	add_fields: ["status", "whatsapp_status"],
	get_indicator(doc) {
		return doc.status === "Paid"
			? [__("Paid"), "green", "status,=,Paid"]
			: [__("Unpaid"), "orange", "status,=,Unpaid"];
	},
};
