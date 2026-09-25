"""HAILM Hackathon: registration, payment, and post-payment fulfilment.

Flow
----
1. Form submit -> `register_and_create_order` creates an Unpaid HAILM Hackathon Registration and
   a Razorpay Order (reusing the existing doctype, so the signed webhook already updates it).
2. Razorpay webhook -> Razorpay Order payment_status changes -> `on_razorpay_order_update`
   (wired in hooks.py) mirrors that onto the registration.
3. On capture, `fulfil` runs after commit: mint a single-use 100% code on the LMS, then send it
   on WhatsApp. Each step is idempotent and records its own status, so a retry never double-issues.
"""

import frappe
from frappe.utils import add_to_date, flt, now_datetime

from . import clients
from .utils import amount_to_paise, clean_full_name, gst_inclusive_breakup, normalize_indian_mobile, split_name

DOCTYPE = "HAILM Hackathon Registration"
PRODUCT_TAG = "hailm_hackathon"
ORDER_REUSE_MINUTES = 30

logger = frappe.logger("hailm_hackathon", allow_site=True, file_count=20)


def offer_amount():
	"""All-in price in INR, from site_config `hailm_hackathon_amount`. None = offer not live."""
	amount = frappe.conf.get("hailm_hackathon_amount")
	return flt(amount) if amount else None


def get_offer():
	amount = offer_amount()
	return {
		"active": bool(amount),
		"amount": amount,
		"currency": "INR",
		"codeEndsAt": frappe.conf.get("hailm_hackathon_code_ends_at") or None,
	}


def _existing_lead(mobile):
	return frappe.db.get_value("CRM Lead", {"mobile_no": mobile}, "name")


def _reusable_order(reg):
	"""An unpaid order from the last 30 minutes can be reopened instead of creating another."""
	if not reg.razorpay_order:
		return None
	order = frappe.db.get_value(
		"Razorpay Order", reg.razorpay_order, ["name", "order_id", "status", "amount", "creation"], as_dict=True
	)
	if not order or order.status not in ("Created", "Attempted") or not order.order_id:
		return None
	if order.creation < add_to_date(now_datetime(), minutes=-ORDER_REUSE_MINUTES):
		return None
	if flt(order.amount) != flt(offer_amount()):
		return None  # price changed since; make a fresh order at the current price
	return order


def _razorpay_order_payload(order_doc, amount, reg):
	return {
		"amount": amount_to_paise(amount),
		"currency": "INR",
		"receipt": order_doc.name,
		"notes": {"product": PRODUCT_TAG, "registration": reg.name},
	}


def _checkout_response(reg, order_id, amount):
	return {
		"status": "unpaid",
		"registration": reg.name,
		"token": reg.public_token,
		"order": {"id": order_id, "amount": amount_to_paise(amount), "currency": "INR"},
		"prefill": {"name": reg.full_name, "contact": reg.mobile_no},
	}


def register_and_create_order(full_name, mobile, attribution=None):
	amount = offer_amount()
	if not amount:
		frappe.throw("Registrations are not open yet.", title="Offer not live")

	full_name = clean_full_name(full_name)
	mobile = normalize_indian_mobile(mobile)
	attribution = attribution or {}

	# One registration per phone number: a returning visitor resumes, a payer is not charged twice.
	existing = frappe.db.get_value(DOCTYPE, {"mobile_no": mobile}, "name")
	if existing:
		reg = frappe.get_doc(DOCTYPE, existing)
		if reg.status == "Paid":
			return {"status": "paid", "registration": reg.name, "token": reg.public_token}
		reg.full_name = full_name
		reused = _reusable_order(reg)
		if reused:
			reg.save(ignore_permissions=True)
			return _checkout_response(reg, reused.order_id, reused.amount)
	else:
		reg = frappe.get_doc({
			"doctype": DOCTYPE,
			"full_name": full_name,
			"mobile_no": mobile,
			"status": "Unpaid",
			"amount": amount,
			"public_token": frappe.generate_hash(length=32),
			"existing_lead": _existing_lead(mobile),
			"utm_source": attribution.get("custom_utm_source"),
			"utm_medium": attribution.get("custom_utm_medium"),
			"utm_campaign": attribution.get("custom_utm_campaign"),
			"code_status": "Pending",
			"whatsapp_status": "Pending",
		})
		reg.insert(ignore_permissions=True)

	first_name, last_name = split_name(full_name)
	base, gst = gst_inclusive_breakup(amount)
	order_doc = frappe.get_doc({
		"doctype": "Razorpay Order",
		"billing_first_name": first_name,
		"billing_last_name": last_name,
		"billing_mobile_no": mobile,
		"seat_count": 1,
		"subtotal": base,
		"discount_amount": 0,
		"gst_amount": gst,
		"amount": amount,
		"amount_due": amount,
		"amount_paid": 0,
		"currency": "INR",
		"notes": frappe.as_json({"product": PRODUCT_TAG, "registration": reg.name}),
	})
	order_doc.insert(ignore_permissions=True)

	try:
		rp_order = clients_razorpay().order.create(_razorpay_order_payload(order_doc, amount, reg))
	except Exception:
		frappe.log_error(frappe.get_traceback(), f"HAILM Hackathon: Razorpay order failed for {reg.name}")
		frappe.throw("We couldn't start the payment. Please try again in a minute.")

	order_doc.order_id = rp_order["id"]
	order_doc.created_at = rp_order.get("created_at")
	order_doc.status = rp_order["status"].capitalize()
	order_doc.save(ignore_permissions=True)

	reg.razorpay_order = order_doc.name
	reg.amount = amount
	reg.save(ignore_permissions=True)
	logger.info(f"{reg.name}: order {order_doc.name} / {order_doc.order_id} for {amount}")
	return _checkout_response(reg, order_doc.order_id, amount)


def clients_razorpay():
	# Same account and keys as the course checkout; imported lazily to keep this module light.
	from humain_learning.razorpay_integration.api import razorpay_client

	return razorpay_client()


def registration_status(token):
	if not token:
		return None
	name = frappe.db.get_value(DOCTYPE, {"public_token": token}, "name")
	if not name:
		return None
	reg = frappe.get_doc(DOCTYPE, name)
	status = {"status": reg.status.lower(), "firstName": split_name(reg.full_name)[0]}
	if reg.status == "Paid":
		# Shown on the thank-you page too, so a student is never stuck waiting on WhatsApp.
		status["code"] = reg.lms_discount_code or None
		status["codeStatus"] = reg.code_status
		status["whatsappStatus"] = reg.whatsapp_status
	return status


# --- webhook hook -----------------------------------------------------------------------------

def on_razorpay_order_update(order_doc, method=None):
	"""doc_events hook on Razorpay Order. A no-op for every order that isn't ours."""
	if not order_doc.has_value_changed("status"):
		return
	name = frappe.db.get_value(DOCTYPE, {"razorpay_order": order_doc.name}, "name")
	if not name:
		return

	reg = frappe.get_doc(DOCTYPE, name)
	if reg.status == "Paid":
		return  # never downgrade a paid registration, e.g. on a late 'failed' for an older attempt

	if order_doc.status == "Paid":
		reg.status = "Paid"
		reg.paid_at = now_datetime()
		reg.payment_id = order_doc.payment_id
		reg.save(ignore_permissions=True)
		frappe.enqueue(
			"humain_learning.hailm_hackathon.services.fulfil",
			registration=reg.name,
			queue="short",
			timeout=120,
			enqueue_after_commit=True,
		)
	elif order_doc.status == "Failed":
		reg.status = "Failed"
		reg.save(ignore_permissions=True)


# --- fulfilment -------------------------------------------------------------------------------

def fulfil(registration):
	"""Issue the LMS code, then WhatsApp it. Safe to call repeatedly."""
	reg = frappe.get_doc(DOCTYPE, registration)
	if reg.status != "Paid":
		return

	if not reg.lms_discount_code:
		try:
			code, lms_id = clients.create_lms_discount_code(reg.full_name, reg.name)
			reg.db_set({"lms_discount_code": code, "lms_discount_code_id": lms_id, "code_status": "Generated",
						"fulfilment_error": None})
			frappe.db.commit()
		except Exception as exc:
			reg.db_set({"code_status": "Failed", "fulfilment_error": str(exc)[:1000]})
			frappe.db.commit()
			frappe.log_error(frappe.get_traceback(), f"HAILM Hackathon: LMS code failed for {reg.name}")
			return  # no code, nothing to WhatsApp

	if reg.whatsapp_status == "Sent":
		return
	if not clients.aisensy_configured():
		reg.db_set("whatsapp_status", "Not Configured")
		frappe.db.commit()
		return
	try:
		response = clients.send_aisensy_whatsapp(
			reg.mobile_no,
			split_name(reg.full_name)[0],
			{
				"name": split_name(reg.full_name)[0],
				"full_name": reg.full_name,
				"code": reg.lms_discount_code,
				"redeem_url": frappe.conf.get("hailm_redeem_url") or "https://www.ailiteracymission.org/ai-olympiad",
			},
		)
		reg.db_set({"whatsapp_status": "Sent", "whatsapp_sent_at": now_datetime(),
					"whatsapp_response": response, "fulfilment_error": None})
	except Exception as exc:
		reg.db_set({"whatsapp_status": "Failed", "fulfilment_error": str(exc)[:1000]})
		frappe.log_error(frappe.get_traceback(), f"HAILM Hackathon: WhatsApp failed for {reg.name}")
	frappe.db.commit()
