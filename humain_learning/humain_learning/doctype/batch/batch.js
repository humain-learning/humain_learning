// Copyright (c) 2026, Raghav Kaul and contributors
// For license information, please see license.txt

frappe.ui.form.on("Batch", {
	fetch_batch(frm) {
        frappe.call ({
            method: 'admin.admin.api.canvas.get_single_course_details',
            args: {
                course_id: frm.doc.course_id,
                template: false
            },
            callback: function(r) {
            if(!r.exc) {
                frm.set_value('course_name', r.message.course_name);
                frm.set_value('course_code', r.message.course_code);
                frm.set_value('sub_account', r.message.sub_account);
                frm.set_value('state', r.message.state);
                frm.set_value('start_date', r.message.start_date);
                frm.set_value('end_date', r.message.end_date);
            }
        }
    })
        
	},
});

frappe.ui.form.on("Itinerary", {
    date(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        if (!row.date) {
            frappe.model.set_value(cdt, cdn, "day", "");
            return;
        }

        const day = frappe.datetime
            .str_to_obj(row.date)
            .toLocaleDateString("en-US", { weekday: "long" });
        frappe.model.set_value(cdt, cdn, "day", day);
    },
});
