import frappe
import razorpay
from razorpay.errors import SignatureVerificationError
from frappe.utils import cint, now_datetime
from humain_learning.utils import validate_required_fields
from werkzeug.exceptions import MethodNotAllowed

frappe.utils.logger.set_log_level("DEBUG")
logger = frappe.logger("razorpay", with_more_info=True, allow_site=True, file_count=50)


def razorpay_client():
	return razorpay.Client(auth=(frappe.conf.razorpay_key_id, frappe.conf.razorpay_key_secret))

@frappe.whitelist(allow_guest=True)
def verify_payment():
	if frappe.request.method != "POST":
		frappe.response.http_status_code = 405
		return {"error": "Method Not Allowed"}
	
	data = frappe.request.get_json()
	required_fields = ["razorpay_order_id", "razorpay_payment_id", "razorpay_signature", "receipt"]

	validate_required_fields(required_fields, data)

	try:
		order_doc = frappe.get_doc("Razorpay Order", data["receipt"])
		if order_doc.order_id != data["razorpay_order_id"]:
			frappe.response.http_status_code = 400
			frappe.throw("Order ID does not match Receipt")
	except frappe.DoesNotExistError as e:
		frappe.throw("Order not found", exc=e)

	if order_doc.status == "Paid":
		frappe.response.http_status_code = 200
		return {"status": "Payment Verified"}
	
	try:
		client = razorpay_client()
		client.utility.verify_payment_signature({
			"razorpay_order_id": order_doc.order_id,
			"razorpay_payment_id": data["razorpay_payment_id"],
			"razorpay_signature": data["razorpay_signature"],
		})

	except SignatureVerificationError:
		logger.warning(
			f"Signature verification failed for order {order_doc.name}"
		)
		frappe.response.http_status_code = 400
		frappe.sendmail(
			recipients=["raghav.kaul@humainlearning.ai"],
			subject=f"Razorpay Verification Failure - {order_doc.name}",
			message=f"""
			Order: {order_doc.name}<br>
			Razorpay Order ID: {data['razorpay_order_id']}<br>
			Razorpay Payment ID: {data['razorpay_payment_id']}<br>
			Stored Order ID: {order_doc.order_id}<br>
			Timestamp: {now_datetime()}<br>
			""",
			now=True,
		)
		return {
			"error": "Invalid payment signature"
		}
	except Exception as e:
		logger.error(
			f"Error verifying payment for order {order_doc.name}: {str(e)}"
		)
		frappe.response.http_status_code = 500
		return {
			"error": "Internal server error"
		}
	
	order_doc.update({
		"payment_id": data["razorpay_payment_id"],
		"attempts": order_doc.attempts + 1,
		"rp_signature": data["razorpay_signature"],
	})

	order_doc.save()
	frappe.response.http_status_code = 200
	frappe.response.message = "Payment verified"
	return 
	


	# if verified:
	# 	order_doc.payment_id = data["razorpay_payment_id"]
	# 	order_doc.status = "Attempted"
	# 	order_doc.amount_paid = order_doc.amount
	# 	order_doc.amount_due = 0
	# 	order_doc.rp_signature = data["razorpay_signature"]
	# 	order_doc.save(ignore_permissions=True)

	# 	frappe.response.http_status_code = 200
	# 	return {"status": "Payment Verified"}

	# frappe.response.http_status_code = 400
	# return {"error": "Payment verification failed"}


### Payment Statuses:
# Keep payment on created for a stipulated amount of time, if not paid, mark as expired


@frappe.whitelist(allow_guest=True)
def create_order():
	if frappe.request.method != "POST":
		raise MethodNotAllowed(valid_methods=["GET"])
	
	data = frappe.request.get_json()
	logger.info(f"Received Order Request: {data}")
	validate_checkout_payload(data)
	logger.info(f"Payload Passed validation: {data}")
	
	cache_key = f'{data.get("billing").get("email")}:{data.get("batchId")}:{data.get("seatCount")}:{data.get("couponCode")}'
	
	lock_key = f"lock:{cache_key}"

	with frappe.cache.lock(lock_key, timeout=30):
		dup_order = frappe.cache.get_value(cache_key)


		if dup_order:
			logger.info(f"Duplicate order found in cache for key {cache_key}: {dup_order}")
			order_doc = frappe.get_doc("Razorpay Order", dup_order)
			if order_doc.status == "Paid":
				frappe.response.http_status_code = 200
				frappe.response.message = "Order already Completed"
				return
			elif order_doc.status in ["Created", "Attempted"]:
				message = {
					"leadId" : order_doc.lead,
					"order": {
						"amount": order_doc.amount,
						"amount_due": order_doc.amount_due,
						"amount_paid": order_doc.amount_paid,
						"attempts": order_doc.attempts,
						"currency": order_doc.currency,
						"entity": "order",
						"id": order_doc.order_id,
						"notes": order_doc.notes,
						"offer_id": None,
						"receipt": order_doc.name,
						"status": order_doc.status.lower(),
					}
				}
				frappe.response.http_status_code = 201
				frappe.response.message = message
				return
		else:

			if len(data.get("learners")) < 1:
				frappe.response.http_status_code = 400
				frappe.response.message = "No Learners provided"
				logger.info(f"Order creation failed due to no learners provided")
				return
			if data.get("seatCount") < 1:
				frappe.response.http_status_code = 400
				frappe.response.message = "Seat Count cannot be less than 1"
				logger.info(f"Order creation failed due to invalid seat count: {data.get('seatCount')}")
				return
			if len(data.get("learners")) != data.get("seatCount"):
				frappe.response.http_status_code = 400
				frappe.response.message = "Number of Learners do not match No of Seats"
				logger.info(f"Order creation failed due to mismatch in learners and seat count: {len(data.get('learners'))} learners, {data.get('seatCount')} seats")
				return
			

			lead_id = data.get("leadId")

			details = frappe._dict(data["billing"])

			lead_data = {
				"doctype": "CRM Lead",
				"first_name": details.firstName,
				"last_name": details.lastName,
				"email": details.email,
				"mobile_no": details.mobile,
				"custom_city": details.city or "",
			}

			if lead_id and frappe.db.exists("CRM Lead", lead_id):
				lead = frappe.get_doc("CRM Lead", lead_id)
				print(f"Existing lead found with ID {lead_id}")
				logger.info(f"Existing lead found with ID {lead_id}")
			else:
				lead = frappe.get_doc(lead_data)
				lead.insert(ignore_permissions=True)
				print(f"Created new lead with ID {lead.name}")
				logger.info(f"Created new lead with ID {lead.name}")


			try:
				course = frappe.get_doc("Template Course", data.get("courseId"))
				print(f"Course fetched: {course.name}")
				logger.info(f"Course fetched: {course.name}")
			except frappe.DoesNotExistError:
				frappe.response.http_status_code = 404
				frappe.response.message = "Course not found"
				logger.info(f"Course not found with ID {data.get('courseId')}")
				return
			
			try:
				batch = frappe.get_doc("Batch", data.get("batchId"))
				print(f"Batch fetched: {batch.name}")
			except frappe.DoesNotExistError:
				frappe.response.http_status_code = 404
				frappe.response.message = "Batch not found"
				return
			
			if not check_batch_validity(batch, course.name):
				return
			
			print(f"Batch {batch.name} is valid for enrollment")

			coupon_code = data.get("couponCode")
			coupon = None
			if coupon_code:
				coupon = check_coupon_validity(coupon_code, course.name)
				if not coupon:
					return
			
			subtotal, discount_amount, gst_amount, amount = calculate_checkout_amounts(course, data.get("seatCount"), coupon)

			deal_name = lead.convert_to_deal(deal={
				"status": "Checkout Attempted"
			})

			print(f"converted lead {lead.name} to deal {deal_name}. Status: 'Checkout Attempted'")
			logger.info(f"converted lead {lead.name} to deal {deal_name}. Status: 'Checkout Attempted'")
			order_doc = frappe.get_doc({
				"doctype": "Razorpay Order",
				"lead": lead.name,
				"deal": deal_name,
				"billing_first_name": data["billing"]["firstName"],
				"billing_last_name": data["billing"]["lastName"],
				"billing_email": data["billing"]["email"],
				"billing_mobile_no": data["billing"]["mobile"],
				"billing_city": data["billing"]["city"],
				"course": course.name,
				"batch": batch.name,
				"seat_count": data.get("seatCount"),
				"subtotal": subtotal,
				"discount_amount": discount_amount,
				"gst_amount": gst_amount,
				"coupon_code": coupon.name if coupon else None,
				"amount": amount,
				"amount_due": amount,
				"amount_paid": 0,
				"currency": "INR",
				"learners": [
					{
						"first_name": learner["firstName"],
						"last_name": learner["lastName"],
						"email": learner["email"],
						"mobile_no": learner["mobile"]
					}
					for learner in data.get("learners")
				],
			})

			order_doc.insert(ignore_permissions=True)

			logger.info(f"Created Razorpay Order document {order_doc.name} for deal {order_doc.deal} with amount {order_doc.amount}")

			try:
				rpclient = razorpay_client()
				order = rpclient.order.create({
					"amount": cint(amount) * 100,
					"currency": order_doc.currency,
					"receipt": order_doc.name,
				})
			except Exception:
				logger.error(frappe.get_traceback(), "Razorpay Order Creation failed")
				frappe.response.http_status_code = 500
				return {"error": "Payment verification failed"}
			
			order_doc.order_id = order["id"]
			order_doc.created_at = order["created_at"]
			order_doc.status = order["status"].capitalize()
			order_doc.save(ignore_permissions=True)
			
			frappe.cache.set_value(cache_key, order_doc.name, expires_in_sec=1800)

			message = {
				"leadId" : lead.name,
				"order": order
			}
			frappe.response.http_status_code = 200
			logger.info(f"Updated Order document {order_doc.name} with Razorpay order ID {order_doc.order_id} and status {order_doc.status}")
			frappe.response.message = message
			return
		
@frappe.whitelist(allow_guest=True)
def razorpay_webhook():
	body = frappe.request.get_data(as_text=True)
	signature = frappe.request.headers.get("X-Razorpay-Signature")
	
	try:
		client = razorpay_client()
		client.utility.verify_webhook_signature(body, signature, frappe.conf.razorpay_webhook_secret)
		print(f"Razorpay Webhook signature verified successfully")
		logger.info("Razorpay Webhook signature verified successfully")
	except SignatureVerificationError:
		logger.warning("Razorpay Webhook signature verification failed")
		frappe.response.http_status_code = 400
		frappe.throw("Invalid Razorpay Webhook Signature")

	request = frappe.request.get_json()
	payment = request.get("payload").get("payment").get("entity")
	event = request.get("event")
	lock_key = f"lock:{payment.get('order_id')}"
	logger.info(
		f"Acquiring lock {lock_key}"
	)
	with frappe.cache.lock(lock_key, timeout=60):
		logger.info(
			f"Acquired lock {lock_key}"
		)
		order_doc=frappe.get_doc("Razorpay Order", {"order_id": payment.get("order_id")})
		logger.info(f"Processing Razorpay Webhook for Order {order_doc.name} with event {event} and payment ID {payment.get('id')}")

		if not order_doc.payment_id:
			order_doc.payment_id = payment.get("id")
		
		if event == "payment.authorized":
			if order_doc.payment_status == "Captured":
				frappe.response.http_status_code = 200
				frappe.response.message = "Payment Already Captured"
				logger.info(f"Payment already captured for Order {order_doc.name}. No update performed.")
				return
			else:
				order_doc.payment_status = "Authorized"
				order_doc.status = "Attempted"
				logger.info(f"Updated Order document {order_doc.name} with payment status {order_doc.payment_status}, amount due {order_doc.amount_due}, and overall status {order_doc.status}")
		elif event == "payment.captured":
			if order_doc.payment_status == "Captured":
				frappe.response.http_status_code = 200
				frappe.response.message = "Payment Already Captured"
				logger.info(f"Payment already captured for Order {order_doc.name}. No update performed.")
				return
			order_doc.payment_status = "Captured"
			order_doc.status = "Paid"
			order_doc.amount_paid = payment.get('amount')/100
			logger.info(f"Updated Order document {order_doc.name} with payment status {order_doc.payment_status}, amount paid {order_doc.amount_paid}, and overall status {order_doc.status}")
		elif event == "payment.failed":
			if order_doc.payment_status == "Captured":
				frappe.response.http_status_code = 200
				frappe.response.message = "Payment Already Captured"
				logger.info(f"Payment already captured for Order {order_doc.name}. No update performed.")
				return
			else:
				order_doc.payment_status = "Failed"
				order_doc.status = "Failed"
				logger.info(f"Updated Order document {order_doc.name} with payment status {order_doc.payment_status}, amount due {order_doc.amount_due}, and overall status {order_doc.status}")

		order_doc.save(ignore_permissions=True)
		frappe.db.commit()
		fresh = frappe.get_doc("Razorpay Order", order_doc.name)
		logger.info("Order Status: ",fresh.status, "Payment Status: ", fresh.payment_status)
		# logger.info(f"FINALLY Updated Order document {order_doc.name} with payment status {order_doc.payment_status}, amount due {order_doc.amount_due}, and overall status {order_doc.status}")
		frappe.response.http_status_code = 200
		frappe.response.message = "Webhook processed successfully"
		return

def validate_checkout_payload(payload):
	required_fields = [
		"billing",
		"courseId",
		"batchId",
		"seatCount",
		"learners",
	]
	required_learner_fields = [
		"firstName",
		"lastName",
		"email",
		"mobile",
	]
	required_billing_fields = [
		"firstName",
		"lastName",
		"email",
		"mobile",
		"city",
	]
	
	validate_required_fields(required_fields, payload)
	for learner in payload.get("learners"):
		validate_required_fields(required_learner_fields, learner)

	validate_required_fields(required_billing_fields, payload.get("billing"))

	return True

def check_batch_validity(batch, course_id):

	if batch.template != course_id:
		print("batch template mismatch")
		frappe.response.http_status_code = 422
		frappe.response.message = "Batch does not belong to selected course"
		frappe.response["error"] = "BATCH ERROR"
		return False
	if batch.enabled == 0:
		print("batch not enabled")
		frappe.response.http_status_code = 422
		frappe.response.message = "Batch is not available for enrollment"
		frappe.response["error"] = "BATCH ERROR"
		return False
	if batch.sold_out == 1:
		print("batch sold out")
		frappe.response.http_status_code = 422
		frappe.response.message = "Batch is not available for enrollment"
		frappe.response["reason"] = "Sold Out"
		frappe.response["error"] = "BATCH ERROR"
		return False
	
	import datetime
	if batch.start_date <= datetime.datetime(year=2026, month=6, day=1):
		print("batch already started")
		frappe.response.http_status_code = 422
		frappe.response.message = "Batch is not available for enrollment"
		frappe.response["reason"] = "Batch has already started"
		frappe.response["error"] = "BATCH ERROR"
		return False
	return True
	
def check_coupon_validity(coupon_code, course_id):

	try:
		doc = frappe.get_doc("Coupon Code", coupon_code)
	except frappe.DoesNotExistError:
		frappe.response.http_status_code = 404
		frappe.response.message = "Sorry! This coupon code does not exist"
		frappe.response["error"] = "COUPON ERROR"
		return False

	if doc.course != course_id:
		frappe.response.http_status_code = 422
		frappe.response.message = "Uh oh! This coupon code is invalid"
		frappe.response["error"] = "COUPON ERROR"
		return False
	
	elif doc.active == 0:
		frappe.response.http_status_code = 422
		frappe.response.message = "This coupon code has expired"
		frappe.response["error"] = "COUPON ERROR"
		return False
	
	return doc


def calculate_checkout_amounts(course, seat_count, coupon=None):
	subtotal = course.price * int(seat_count)
	discount_amount = 0
	if coupon:
		if coupon.type == "Flat":
			discount_amount = float(coupon.amount)
		elif coupon.type == "Percentage":
			discount_amount = subtotal * (float(coupon.percentage) / 100)
	gst_amount = (subtotal - discount_amount) * 0.18
	amount = subtotal - discount_amount + gst_amount
	return subtotal, discount_amount, gst_amount, amount