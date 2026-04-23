# Copyright (c) 2026, Raghav Kaul and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BolnaCallStatus(Document):
	def validate(self):
		self.title = self.id.capitalize()

		