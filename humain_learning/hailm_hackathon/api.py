"""Endpoints for the HAILM Hackathon.

`register`, `status` and `get_offer` are not guest-accessible: the humainlearning.ai Next.js
site calls them server-side with its Frappe API token, like the existing lead/order routes.

`razorpay_webhook` is guest-accessible because Razorpay calls it; every request is rejected
unless its HMAC signature matches `hailm_razorpay_webhook_secret`.
"""

import frappe

from . import services
from .utils import ValidationError, verify_razorpay_signature


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
		return services.register(
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


@frappe.whitelist(allow_guest=True, methods=["POST"])
def razorpay_webhook():
	"""Point a Razorpay webhook (events: payment.captured, order.paid) at this method.

	URL: https://<site>/api/method/humain_learning.hailm_hackathon.api.razorpay_webhook
	"""
	secret = frappe.conf.get("hailm_razorpay_webhook_secret")
	raw_body = frappe.request.get_data()
	signature = frappe.request.headers.get("X-Razorpay-Signature")
	if not verify_razorpay_signature(raw_body, signature, secret):
		frappe.response.http_status_code = 400
		return {"error": "Invalid signature"}

	event = frappe.parse_json(raw_body.decode()) if raw_body else {}
	try:
		note = services.handle_webhook(event)
	except Exception:
		# A non-2xx makes Razorpay retry; handle_webhook is idempotent, so retries are safe.
		frappe.log_error(frappe.get_traceback(), "HAILM Hackathon: webhook processing failed")
		frappe.response.http_status_code = 500
		return {"error": "processing failed"}
	return {"status": "ok", "note": note}


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
