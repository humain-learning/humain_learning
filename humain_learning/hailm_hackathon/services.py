"""HAILM Hackathon: registration, Razorpay Payment Page, and post-payment fulfilment.

Flow
----
1. Form submit -> `register` creates (or resumes) an Unpaid HAILM Hackathon Registration and
   returns the Razorpay Payment Page URL, prefilled with the student's name, phone and
   registration id. There is no checkout on our side.
2. The student pays on the hosted Payment Page.
3. Razorpay -> our own webhook (`api.razorpay_webhook`, own secret) -> `handle_webhook` matches
   the captured payment to a registration and marks it Paid.
4. `fulfil` runs after commit: mint a single-use 100% code on the LMS, then send it on WhatsApp.
   Each step is idempotent and records its own status, so a retry never double-issues.

Matching a payment to a registration
------------------------------------
Webhooks are account-wide: every payment on the Razorpay account arrives here, not just the
hackathon's. So a payment is only ever accepted in one of two ways:
  * it carries one of our registration ids in its notes (exact), or
  * its phone matches an Unpaid registration AND its amount equals the hackathon price.
Phone alone is never enough — a registered parent paying for something else must not be marked
Paid. Anything else is ignored.
"""

import frappe
from frappe.utils import flt, now_datetime

from . import clients
from .utils import (
	build_payment_page_url,
	choose_registration,
	clean_full_name,
	first_name,
	normalize_indian_mobile,
)

DOCTYPE = "HAILM Hackathon Registration"
HANDLED_EVENTS = {"payment.captured", "order.paid"}

logger = frappe.logger("hailm_hackathon", allow_site=True, file_count=20)


def _offer_amount():
	amount = frappe.conf.get("hailm_hackathon_amount")
	return flt(amount) if amount else None


def _payment_page_url():
	return frappe.conf.get("hailm_hackathon_payment_page_url") or None


def get_offer():
	"""Live only once both the price and the Payment Page URL are configured."""
	amount = _offer_amount()
	return {
		"active": bool(amount and _payment_page_url()),
		"amount": amount,
		"currency": "INR",
		"codeEndsAt": frappe.conf.get("hailm_hackathon_code_ends_at") or None,
	}


def _existing_lead(mobile):
	return frappe.db.get_value("CRM Lead", {"mobile_no": mobile}, "name")


def register(full_name, mobile, attribution=None):
	page_url = _payment_page_url()
	if not (_offer_amount() and page_url):
		frappe.throw("Registrations are not open yet.", title="Offer not live")

	full_name = clean_full_name(full_name)
	mobile = normalize_indian_mobile(mobile)
	attribution = attribution or {}

	# One registration per phone number: a returning visitor resumes, a payer is not sent to pay again.
	existing = frappe.db.get_value(DOCTYPE, {"mobile_no": mobile}, "name")
	if existing:
		reg = frappe.get_doc(DOCTYPE, existing)
		if reg.status == "Paid":
			return {"status": "paid", "registration": reg.name, "token": reg.public_token}
		if reg.full_name != full_name:
			reg.full_name = full_name
			reg.save(ignore_permissions=True)
	else:
		reg = frappe.get_doc({
			"doctype": DOCTYPE,
			"full_name": full_name,
			"mobile_no": mobile,
			"status": "Unpaid",
			"amount": _offer_amount(),
			"public_token": frappe.generate_hash(length=32),
			"existing_lead": _existing_lead(mobile),
			"utm_source": attribution.get("custom_utm_source"),
			"utm_medium": attribution.get("custom_utm_medium"),
			"utm_campaign": attribution.get("custom_utm_campaign"),
			"code_status": "Pending",
			"whatsapp_status": "Pending",
		})
		reg.insert(ignore_permissions=True)

	return {
		"status": "unpaid",
		"registration": reg.name,
		"token": reg.public_token,
		"paymentUrl": build_payment_page_url(page_url, reg.full_name, reg.mobile_no, reg.name),
	}


def registration_status(token):
	if not token:
		return None
	name = frappe.db.get_value(DOCTYPE, {"public_token": token}, "name")
	if not name:
		return None
	reg = frappe.get_doc(DOCTYPE, name)
	status = {"status": reg.status.lower(), "firstName": first_name(reg.full_name)}
	if reg.status == "Paid":
		# Shown on the thank-you page too, so a student is never stuck waiting on WhatsApp.
		status["code"] = reg.lms_discount_code or None
		status["codeStatus"] = reg.code_status
		status["whatsappStatus"] = reg.whatsapp_status
	return status


# --- webhook -----------------------------------------------------------------------------------

def _match_registration(payment):
	"""Return (registration name, how it matched) or (None, reason). Logic lives in utils."""
	return choose_registration(
		payment,
		expected_amount=_offer_amount(),
		registration_exists=lambda name: frappe.db.exists(DOCTYPE, name),
		unpaid_registration_for_mobile=lambda mobile: frappe.db.get_value(
			DOCTYPE, {"mobile_no": mobile, "status": "Unpaid"}, "name"
		),
	)


def handle_webhook(event):
	"""Process a signature-verified Razorpay webhook. Returns a short note for the log."""
	if event.get("event") not in HANDLED_EVENTS:
		return "ignored event"
	payment = ((event.get("payload") or {}).get("payment") or {}).get("entity") or {}
	if payment.get("status") != "captured" or not payment.get("id"):
		return "not a captured payment"

	payment_id = payment["id"]
	with frappe.cache.lock(f"lock:hailm_hackathon:{payment_id}", timeout=60):
		# payment.captured and order.paid both arrive for one payment; handle it once.
		if frappe.db.exists(DOCTYPE, {"payment_id": payment_id}):
			return "already processed"

		name, how = _match_registration(payment)
		if not name:
			return f"no match: {how}"

		reg = frappe.get_doc(DOCTYPE, name)
		if reg.status == "Paid":
			# A second payment for someone already paid: keep it visible for a refund decision.
			reg.db_set("extra_payments", "\n".join(filter(None, [reg.extra_payments, payment_id])))
			frappe.log_error(f"Second payment {payment_id} for already-paid {reg.name}", "HAILM Hackathon: duplicate payment")
			return "duplicate payment recorded"

		reg.status = "Paid"
		reg.paid_at = now_datetime()
		reg.payment_id = payment_id
		reg.amount_paid = flt(payment.get("amount")) / 100
		reg.match_method = how
		reg.webhook_payload = frappe.as_json(payment)[:10000]
		reg.save(ignore_permissions=True)

	frappe.enqueue(
		"humain_learning.hailm_hackathon.services.fulfil",
		registration=name,
		queue="short",
		timeout=120,
		enqueue_after_commit=True,
	)
	logger.info(f"{name}: paid via {payment_id} ({how})")
	return f"paid: {name}"


# --- fulfilment --------------------------------------------------------------------------------

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
			first_name(reg.full_name),
			{
				"name": first_name(reg.full_name),
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
