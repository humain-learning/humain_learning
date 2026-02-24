# Copyright (c) 2026, Raghav Kaul and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe

class WebinarMapping(Document):
    def validate(self):
        
        exists = frappe.db.exists(
			"Webinar Mapping",
			{
				"form_id": self.form_id,
				"name": ["!=", self.name]
			}
		)
        
        if exists:
            frappe.throw("Mapping for this form already exists")