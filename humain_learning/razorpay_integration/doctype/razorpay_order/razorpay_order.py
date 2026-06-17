# Copyright (c) 2026, Raghav Kaul and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RazorpayOrder(Document):
	def on_update(self):
		self.amount_due = self.amount - self.amount_paid

		if self.has_value_changed("payment_status") and self.payment_status == "Captured":
			if self.coupon_code:
				coupon_doc = frappe.get_doc("Coupon Code", self.coupon_code)
				coupon_doc.use_count += 1
				coupon_doc.save()