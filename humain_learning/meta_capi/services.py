import frappe
import time
from frappe.utils import now
from .utils import sha256_hash, sha256_hash_phone
from.client import send_meta_event
import re

def process_meta_capi_event(doc, method):

	events= frappe.get_all("Meta CAPI Event", filters={"reference_doctype": doc.doctype, "enabled":1}, pluck="name")
	if not events:
		return
	
	for event in events:
		event_doc = frappe.get_doc("Meta CAPI Event", event)

		if not frappe.safe_eval(event_doc.condition, None, {"doc": doc}):
			continue
		
		event_id = f"{event_doc.name}:{doc.name}"
		if frappe.db.exists("Meta Event Log", event_id):
			frappe.logger("meta_capi").warning(f"Event {event_id} already exists. Skipping...")
			continue
		
		
		frappe.logger("meta_capi").warning(f"Event {event_id} request initiated.")
		process_meta_event(event_id, doc, event_doc)


def process_meta_event(event_id, doc, event):

	if doc.doctype == "CRM Lead":
		lead_id = doc.facebook_lead_id
	elif doc.doctype == "CRM Deal":
		lead_id = frappe.db.get_value("CRM Lead", doc.lead, "facebook_lead_id")

	custom_data = {
		"lead_event_source": "FCRM",
		"event_source": "crm"
	}

	if event.event_name == "Purchase":
		custom_data["currency"] = "INR"
		custom_data["value"] = doc.deal_value

	payload = {
		"data": [
			{
				"event_name": event.event_name,
				"event_time": int(time.time()),
				"event_id": event_id,
				"action_source": "system_generated",
				"user_data": {
					"em": [sha256_hash(doc.email)],
					"ph": [sha256_hash_phone(doc.mobile_no)],
					"fn": [sha256_hash(doc.first_name)],
					"ln": [sha256_hash(doc.last_name)],
					"ct": [sha256_hash(doc.custom_city)],
					"country": [sha256_hash("in")],
					"lead_id": lead_id
				},
				"custom_data": custom_data
			}
		]
	}
	event_log = frappe.get_doc({
			"doctype": "Meta Event Log",
			"event_id": event_id,
			"meta_event": event.name,
			"event_name": event.event_name,
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"status": "Pending",
			"timestamp": now(),
			"unix_time": int(time.time()),
			"request_body": payload
		})
	event_log.insert(ignore_permissions=True)
	frappe.db.commit()

	response = send_meta_event(event_id, payload)
	event_log.http_code = response.status_code
	event_log.save()
	frappe.db.commit()
	event_log.reload()
	try:
		data = response.json()
	except Exception as e:
		event_log.status = "Error"
		event_log.error_message = f"Failed to parse response JSON: {str(e)}"
		event_log.response_body = {"raw_text": response.text[:1000]}
		event_log.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.logger("meta_capi").error(f"Event {event_id} failed to parse. Status: {response.status_code}, Body: {response.text[:200]}")
		return
	
	event_log.fbtrace_id = data.get("fbtrace_id")


	if response.status_code == 200:
		if data.get("events_received") == 1:
			event_log.status = "Success"
			event_log.response_body = data
			
			frappe.logger("meta_capi").warning(f"Event {event_id} received successfully.")
		else:
			event_log.status = "Error"
			frappe.logger("meta_capi").error(f"Event {event_id} sent but was dropped by Meta.")
			event_log.error_message = "Event dropped by Meta"
			event_log.response_body = data
	elif response.status_code == 400:
		event_log.status = "Error"
		frappe.logger("meta_capi").error(f"Bad Request for Event {event_id}. Check response for details.")
		event_log.response_body = data
		event_log.error_message = data.get("error", {}).get("message")
	elif response.status_code == 401 or response.status_code == 403:
		event_log.status = "Error"
		frappe.logger("meta_capi").error(f"Unauthorized: Invalid Access Token for Event {event_id}.")
		event_log.response_body = data
		event_log.error_message = data.get("error", {}).get("message")
	else:
		event_log.status = "Error"
		event_log.error_message = f"HTTP {response.status_code}"
		event_log.response_body = {"error":response.text[:1000]}

	event_log.save(ignore_permissions=True)
	frappe.db.commit()


