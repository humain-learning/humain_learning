# Copyright (c) 2026, Raghav Kaul and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class Itinerary(Document):
	def validate(self):
		if self.date:
			self.day = getdate(self.date).strftime("%A")
		else:
			self.day = ""

		if self.doubt_clearing and self.graduation:
			frappe.throw("Doubt Clearing and Graduation cannot be selected at the same time.")
		if self.time_tbd:
			self.time = None
			self.duration = None