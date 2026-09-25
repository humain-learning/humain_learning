"""Endpoints for the HAILM Hackathon landing page on humainlearning.ai.

Not guest-accessible: the Next.js site calls these server-side with its Frappe API token,
exactly like the existing create_order/submit_lead routes. Browsers never hit Frappe directly.
"""

import frappe

from . import services
from .utils import ValidationError

frappe.utils.logger.set_log_level("INFO")


def _bad_request(message):
	frappe.response.http_status_code = 400
	return {"error": message}


@frappe.whitelist(methods=["GET"])
def get_offer():
	return services.get_offer()


@frappe.whitelist(methods=["POST"])
def register():
	data = frappe.request.get_json(silent=True) or {}
	try:
		return services.register_and_create_order(
			full_name=data.get("fullName"),
			mobile=data.get("mobile"),
			attribution=data.get("attribution") or {},
		)
	except ValidationError as exc:
		return _bad_request(str(exc))


@frappe.whitelist(methods=["GET"])
def status(token=None):
	result = services.registration_status(token)
	if result is None:
		frappe.response.http_status_code = 404
		return {"error": "Registration not found"}
	return result


@frappe.whitelist(methods=["POST"])
def retry_fulfilment(registration):
	"""Desk button: re-run code generation / WhatsApp for a paid registration."""
	frappe.only_for(("System Manager", "Sales Manager"))
	reg = frappe.get_doc(services.DOCTYPE, registration)
	if reg.status != "Paid":
		frappe.throw("Only paid registrations can be fulfilled.")
	if reg.whatsapp_status in ("Failed", "Not Configured"):
		reg.db_set("whatsapp_status", "Pending")
	frappe.enqueue(
		"humain_learning.hailm_hackathon.services.fulfil",
		registration=registration,
		queue="short",
		timeout=120,
		enqueue_after_commit=True,
	)
	return {"queued": True}
