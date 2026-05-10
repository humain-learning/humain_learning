# Copyright (c) 2026, Raghav Kaul and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class MetaEventLog(Document):
	def before_insert(self):
		if not self.event_id:
			self.event_id = f"{self.meta_event}:{self.reference_name}"

		if not self.status:
			self.status = "Pending"