frappe.listview_settings["CRM Lead"] = {
	onload(listview) {
		listview.page.add_action_item(__("Retry Bolna Lifecycle"), () => {
			const checked_items = listview.get_checked_items();
			const leads = checked_items.map((item) => item.name);

			if (!leads.length) {
				frappe.msgprint(__("Select at least one lead."));
				return;
			}

			frappe.confirm(
				__("Retrigger Bolna lifecycle for {0} selected leads?", [leads.length]),
				() => {
					frappe.call({
						method: "humain_learning.bolna.lead_hooks.retry_bolna_lifecycle_bulk",
						args: { leads },
						freeze: true,
						freeze_message: __("Retriggering Bolna lifecycle..."),
						callback: (r) => {
							const res = r.message || {};
							frappe.msgprint(
								__(
									"Bolna retrigger complete.<br>Total: {0}<br>Success: {1}<br>Failed: {2}",
									[res.total || 0, res.succeeded || 0, res.failed || 0]
								)
							);
							listview.refresh();
						},
					});
				}
			);
		});
	},
};
