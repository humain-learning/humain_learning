# Copyright (c) 2026, Raghav Kaul and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.data import validate_python_code
from frappe.model.document import Document


class MetaCAPIEvent(Document):
	def validate(self):
		self.validate_condition()
		if self.reference_doctype not in ["CRM Lead", "CRM Deal"]:
			frappe.throw(_("Reference Doctype must be either 'CRM Lead' or 'CRM Deal'"))
		if self.event_name == "Purchase" and self.reference_doctype != "CRM Deal":
			frappe.throw(_("Purchase event can only be associated with CRM Deal"))

	def validate_condition(self):
		if self.condition:
			validate_python_code(self.condition, fieldname=_("Condition"), is_expression=True)
	def get_code_fields(self):
		return {"condition": "PythonExpression"}
