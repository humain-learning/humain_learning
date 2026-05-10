# Copyright (c) 2026, Raghav Kaul and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from ...client import validate_credentials
import json
from types import SimpleNamespace

class MetaCAPICredentials(Document):
	
	def validate(self):
		response = validate_credentials(self)
		data = response.json()

		if response.status_code == 401:
			frappe.throw("Unauthorized: Invalid Access Token")

		if response.status_code == 400:
			if data["error"]["code"] == 100 :
				frappe.throw(str(data))
				# frappe.throw("Invalid Pixel ID")
		if response.status_code != 200:
			frappe.throw(f"Uknown Error Occured in Verification")
		frappe.msgprint(str(data))