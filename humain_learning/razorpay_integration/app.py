import hmac
import hashlib
import json

import frappe
import razorpay
from frappe.utils import cint

def razorpay_client():
	return razorpay.Client(auth=(frappe.conf.razorpay_key_id, frappe.conf.razorpay_key_secret))

@frappe.whitelist(allow_guest=True)
def create_order():
	if frappe.request.method != "POST":
		frappe.response.http_status_code = 405
		return {"error": "Method Not Allowed"}

	data = frappe.request.get_json()
	if not data:
		frappe.response.http_status_code = 400
		return {"error": "Invalid request body"}

	order_doc = frappe.get_doc({
		"doctype": "Razorpay Order",
		"amount": data["amount"],
		"amount_due": data["amount"],
		"amount_paid": 0,
		"currency": data["currency"],
		"notes": data.get("notes", {}),
	})

	order_doc.insert(ignore_permissions=True)
	order_doc.reload()

	try:
		client = razorpay_client()
		order = client.order.create({
			"amount": cint(data["amount"]) * 100,
			"currency": data["currency"],
			"receipt": order_doc.name,
		})
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Razorpay create_order failed")
		frappe.response.http_status_code = 502
		return {"error": "Failed to create payment order. Please try again."}

	order_doc.order_id = order["id"]
	order_doc.status = order["status"].capitalize()
	order_doc.save(ignore_permissions=True)

	return order

@frappe.whitelist(allow_guest=True)
def verify_payment():
	if frappe.request.method != "POST":
		frappe.response.http_status_code = 405
		return {"error": "Method Not Allowed"}

	data = frappe.request.get_json()
	if not data:
		frappe.response.http_status_code = 400
		return {"error": "Invalid request body"}

	try:
		order_doc = frappe.get_doc("Razorpay Order", data["receipt"])
	except frappe.DoesNotExistError:
		frappe.response.http_status_code = 404
		return {"error": "Order not found"}

	# Idempotency: don't re-process an already verified payment
	if order_doc.status == "Paid":
		frappe.response.http_status_code = 200
		return {"status": "Payment Verified"}

	try:
		client = razorpay_client()
		verified = client.utility.verify_payment_signature({
			"razorpay_order_id": order_doc.order_id,
			"razorpay_payment_id": data["razorpay_payment_id"],
			"razorpay_signature": data["razorpay_signature"],
		})
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Razorpay verify_payment failed")
		frappe.response.http_status_code = 400
		return {"error": "Payment verification failed"}

	if verified:
		order_doc.payment_id = data["razorpay_payment_id"]
		order_doc.status = "Paid"
		order_doc.amount_paid = order_doc.amount
		order_doc.amount_due = 0
		order_doc.rp_signature = data["razorpay_signature"]
		order_doc.save(ignore_permissions=True)

		frappe.response.http_status_code = 200
		return {"status": "Payment Verified"}

	frappe.response.http_status_code = 400
	return {"error": "Payment verification failed"}