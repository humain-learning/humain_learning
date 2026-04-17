frappe.listview_settings["Bolna Agent"] = {
    onload(listview) {
        listview.page.add_inner_button(__("Fetch All Agents"), () => {
            frappe.call({
                method: "humain_learning.bolna.services.sync_bolna_agents",
                freeze: true,
                freeze_message: __("Syncing Bolna Agents..."),
            }).then((r) => {
                const new_agents = Number((r && r.message) || 0);
                listview.refresh();
                setTimeout(() => listview.refresh(), 300);
                frappe.show_alert({
                    message: __("Added {0} new agents.", [new_agents]),
                    indicator: "green",
                });
            });
        });
    },
};