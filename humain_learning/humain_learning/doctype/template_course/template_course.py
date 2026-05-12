# Copyright (c) 2026, Raghav Kaul and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class TemplateCourse(Document):	
    def on_update(self):
        if not self.has_value_changed("price"):
            return

        discounts = frappe.get_all(
            "Web Discount",
            filters={"course": self.name},
            pluck="name",
        )

        for name in discounts:
            wd = frappe.get_doc("Web Discount", name)
            wd.base_price = self.price
            wd.save() 