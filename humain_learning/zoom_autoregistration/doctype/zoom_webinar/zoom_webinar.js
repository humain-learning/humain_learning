// Copyright (c) 2026, Raghav Kaul and contributors
// For license information, please see license.txt

frappe.ui.form.on("Zoom Webinar", {
    refresh(frm) {
        if (frm.is_new()) {
            return;
        }

        frm.add_custom_button("Shorten All URLs", () => {
            frappe.call({
                method: "humain_learning.zoom_autoregistration.api.backfill_shorten_urls",
                args: {
                    webinar: frm.doc.name,
                },
                freeze: true,
                freeze_message: __("Queueing URL shortening jobs..."),
                callback(r) {
                    if (r.exc) {
                        return;
                    }

                    frappe.show_alert({
                        message: __("Queued {0} registrants for URL shortening", [r.message.queued || 0]),
                        indicator: "green",
                    });
                }
            });
        });
		frm.add_custom_button("Fetch Webinar Attendance", () => {
			frappe.call({
                method: "humain_learning.zoom_autoregistration.api.queue_attendee_fetch",
                args: {
                    webinar_id: frm.doc.name,
                },
			})
		})
    },

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
					frm.set_value("end_time", r.message.end_time);
                }
            }
        });
    }
});

