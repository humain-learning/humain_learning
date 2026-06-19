# Copyright (c) 2026, Raghav Kaul and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint
from ...services import tick_up_coupon

class RazorpayOrder(Document):
	def validate(self):
		self.amount_due = self.amount - self.amount_paid
	def on_update(self):
		if self.has_value_changed("payment_status") and self.payment_status == "Captured":
			if self.coupon_code:
				tick_up_coupon(self.coupon_code)