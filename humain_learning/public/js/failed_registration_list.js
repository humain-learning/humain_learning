frappe.listview_settings["Failed Registration"] = {

    onload(listview) {

        listview.page.add_inner_button("Retry All", function () {

            frappe.call({
                method: "humain_learning.zoom_autoregistration.api.retry_all_failed_registrations",
                freeze: true,
                freeze_message: "Queueing retries..."
            }).then(() => {
                frappe.msgprint("All retries queued.");
                listview.refresh();
            });

        });

    }

};