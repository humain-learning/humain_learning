# Copyright (c) 2026, Raghav Kaul and contributors
# For license information, please see license.txt

from frappe.model.document import Document
import frappe
from humain_learning.zoom_autoregistration.api import fetch_webinar

class ZoomWebinar(Document):
	
	def validate(self):
		if not self.webinar_id:
			frappe.throw("Webinar ID is required.")

	def after_insert(self):
		# Schedule attendee report
		pass

	def after_insert(self):
		if not self.topic:
			details = fetch_webinar(self.webinar_id)
			self.topic = details.get("topic")
			self.start_time = details.get("start_time")
			self.end_time = details.get("end_time")
			self.host_email = details.get("host_email")
			self.created_at = details.get("created_at")