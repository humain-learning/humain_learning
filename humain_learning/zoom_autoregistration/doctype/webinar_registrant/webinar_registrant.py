# Copyright (c) 2026, Raghav Kaul and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WebinarRegistrant(Document):
	def after_insert(self):
		if self.join_url and not self.join_url.startswith("https://hlai.in"):
			frappe.enqueue(
				method="humain_learning.zoom_autoregistration.api.shorten_url",
				queue="short",
				registrant=self.name,
				enqueue_after_commit=True
			)