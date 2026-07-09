# Copyright (c) 2026, Raghav Kaul and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import cint

class CouponCode(Document):
	
	def before_save(self):
		if self.use_count >= self.max_uses:
			self.active = 0	

	def deactivate(self):
		self.active = 0
