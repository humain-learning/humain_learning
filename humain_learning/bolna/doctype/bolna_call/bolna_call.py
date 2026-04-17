# Copyright (c) 2026, Raghav Kaul and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from ...services import process_extractions, update_lead_status

class BolnaCall(Document):
	def on_update(self):
		if self.has_value_changed("status"):
			update_lead_status(self)
			
		if self.has_value_changed("extracted_data") and self.extracted_data:
			process_extractions(self)

