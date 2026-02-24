// Copyright (c) 2026, Raghav Kaul and contributors
// For license information, please see license.txt

frappe.ui.form.on("Zoom Webinar", {
    fetch_webinar_details(frm) {
        frappe.call({
            method: "humain_learning.zoom_autoregistration.api.fetch_webinar",
            args: {
                webinar_id: frm.doc.webinar_id
            },
            freeze: true,
            callback(r) {
                if (!r.exc) {
                    frm.set_value("topic", r.message.topic);
                    frm.set_value("start_time", r.message.start_time);
                    frm.set_value("created_at", r.message.created_at);
                    frm.set_value("host_email", r.message.host_email);
                }
            }
        });
    }
});

