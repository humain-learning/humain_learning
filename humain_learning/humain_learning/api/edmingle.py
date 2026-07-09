import frappe
from humain_learning.utils import validate_required_fields


logger = frappe.logger("edmingle", with_more_info=True, allow_site=True, file_count=50, max_size=10485760)  # 10MB

@frappe.whitelist(allow_guest=True)
def edmingle_webhook():
	frappe.response.http_status_code = 200
	request = frappe.request.get_json()

	frappe.enqueue(
		method="humain_learning.humain_learning.api.edmingle.process_edmingle_webhook",
		request=request,
		queue="default",
		timeout=300,
	)
	return {"status": "Webhook received"}



def process_edmingle_webhook(request):
	logger.info(f"Processing Edmingle Webhook request: {request}")
	print(f"Processing Edmingle Webhook request: {request}")

	required_fields = ["event", "payload"]

	logger.info(f"Validating required fields {required_fields} on Edmingle Webhook request")
	print(f"Validating required fields {required_fields} on Edmingle Webhook request")
	validate_required_fields(required_fields, request)

	try:
		event = request["event"]["event"]
	except KeyError:
		logger.info(f"Edmingle Webhook missing 'event' field in payload: {request}")
		print(f"Edmingle Webhook missing 'event' field in payload: {request}")
		frappe.throw("Invalid request: 'event' field is missing in the request payload.")
		return
	
	payload = request["payload"]
	logger.info(f"Edmingle Webhook event received: {event}")
	print(f"Edmingle Webhook event received: {event}")

	if event == "transaction.user_purchase_initiated":
		name = payload.get("name")
		ct_code = payload.get("contact_number_dial_code") or ""
		phone = payload.get("contact_number")
		mobile_no = ct_code + phone
		email = payload.get("email")
		logger.info(f"Creating CRM Lead for Edmingle checkout: name={name}, email={email}, mobile_no={mobile_no}")
		print(f"Creating CRM Lead for Edmingle checkout: name={name}, email={email}, mobile_no={mobile_no}")
		lead = frappe.get_doc({
			"doctype": "CRM Lead",
			"first_name": name,
			"email":email,
			"mobile_no": mobile_no,
			"source": "Edmingle Event Checkout",
		})

		logger.info(f"Saving CRM Lead for Edmingle checkout: email={email}")
		print(f"Saving CRM Lead for Edmingle checkout: email={email}")
		lead.save(ignore_permissions=True)

		logger.info(f"Converting CRM Lead {lead.name} to CRM Deal for Edmingle checkout")
		print(f"Converting CRM Lead {lead.name} to CRM Deal for Edmingle checkout")
		deal_name = lead.convert_to_deal(deal={
				"status": "Checkout Attempted"
			})

		logger.info(f"Converted CRM Lead {lead.name} to CRM Deal {deal_name}")
		print(f"Converted CRM Lead {lead.name} to CRM Deal {deal_name}")
		return
	
	elif event == "transaction.user_purchase_completed":
		name = payload.get("name")
		ct_code = payload.get("contact_number_dial_code") or ""
		phone = payload.get("contact_number")
		mobile_no = ct_code + phone
		email = payload.get("email")

		logger.info(f"Fetching CRM Deal for Edmingle purchase completion: email={email}")
		print(f"Fetching CRM Deal for Edmingle purchase completion: email={email}")
		deal = frappe.get_doc("CRM Deal", {"email": email})

		logger.info(f"Updating CRM Deal {deal.name} to Won with deal_value={payload.get('final_price')}")
		print(f"Updating CRM Deal {deal.name} to Won with deal_value={payload.get('final_price')}")
		deal.update({
			"status": "Won",
			"deal_value": payload.get("final_price")
		})

		logger.info(f"Saving CRM Deal {deal.name} for Edmingle purchase completion")
		print(f"Saving CRM Deal {deal.name} for Edmingle purchase completion")
		deal.save(ignore_permissions=True)
		return
	else:
		logger.info(f"Received unhandled Edmingle Webhook event: {event}")
		print(f"Received unhandled Edmingle Webhook event: {event}")
		return
