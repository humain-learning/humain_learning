# Copyright (c) 2026, Raghav Kaul and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Batch(Document):
	def validate(self):
		if self.batch_name.endswith("Batch"):
			self.batch_name = self.batch_name.replace("Batch", "").strip()
		else:
			self.batch_name = self.batch_name.strip()
		
