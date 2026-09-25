frappe.listview_settings["HAILM Hackathon Registration"] = {
	add_fields: ["status", "whatsapp_status"],
	get_indicator(doc) {
		if (doc.status === "Paid") return [__("Paid"), "green", "status,=,Paid"];
		if (doc.status === "Failed") return [__("Failed"), "red", "status,=,Failed"];
		return [__("Unpaid"), "orange", "status,=,Unpaid"];
	},
};
