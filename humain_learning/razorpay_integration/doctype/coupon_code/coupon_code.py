# Copyright (c) 2026, Raghav Kaul and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe import cint

class CouponCode(Document):
	
	def validate(self):
		self.name = self.name.upper()
		if cint(self.max_uses) <= cint(self.use_count):
			self.active = 0
		elif cint(self.max_uses) > cint(self.use_count):
			self.active = 1

