# Copyright (c) 2026, Raghav Kaul and contributors
# For license information, please see license.txt

from frappe.model.document import Document
import frappe
from humain_learning.zoom_autoregistration.api import fetch_webinar
class ZoomWebinar(Document):
	
	def validate(self):
		if not self.webinar_id:
			frappe.throw("Webinar ID is required.")

	def on_save(self):
		fetch_webinar(self.webinar_id)