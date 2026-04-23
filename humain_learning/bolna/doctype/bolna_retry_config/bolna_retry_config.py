# Copyright (c) 2026, Raghav Kaul and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class BolnaRetryConfig(Document):
	def validate(self):
		try:
			intervals = frappe.parse_json(self.retry_interval_minutes) or []
		except Exception:
			frappe.throw("Retry Intervals must be a valid JSON list of integers.")

		if not isinstance(intervals, list):
			frappe.throw("Retry Intervals must be a list of integers.")
		if any(not isinstance(i, int) or i < 0 for i in intervals):
			frappe.throw("Retry Intervals must be a list of non-negative integers.")

		if self.max_retries > 0 and len(intervals) != self.max_retries:
			frappe.throw(f"Number of retry intervals must match max retries ({self.max_retries}).")

	def get_intervals(self):
		return frappe.parse_json(self.retry_interval_minutes) or []
	
	def get_retry_statuses(self):
		return [row.status for row in (self.retry_on_statuses or [])]