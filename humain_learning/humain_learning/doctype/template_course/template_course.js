 // Copyright (c) 2026, Raghav Kaul and contributors
// For license information, please see license.txt

frappe.ui.form.on("Template Course", {
	fetch_course_details(frm) {
        if (!frm.doc.course_id) {
            frappe.throw("Please provide a course ID first.");
            return;
        }
        frappe.call({
            method : 'admin.admin.api.canvas.get_single_course_details',
            args: {
                course_id: frm.doc.course_id ,
                template: true
            },
            callback: function(r) {
                if(!r.exc) {
                    if (r.message.state != 'Unpublished') {
                        frappe.throw("WARNING: The course is published on the LMS. Please make sure the course is unpublished on the lms.")
                    }
                    else {
                        frm.set_value('course_name', r.message.course_name);
                        frm.set_value('code', r.message.course_code);
                        frm.set_value('sub_account', r.message.sub_account);
                    }
                }
            }
        })
	},
});