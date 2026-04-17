import frappe


def update_bolna_call_record(payload):
	execution_id = payload.get("id")
	status = payload.get("status")
	
	doc = frappe.get_doc("Bolna Call", execution_id)
	doc.status = status
	doc.error_message = payload.get("error_message") or ""

	if payload.get("summary"):
		doc.summary = payload.get("summary")
	if payload.get("transcript"):
		doc.transcript = payload.get("transcript")
	if payload.get("extracted_data") is not None:
		doc.extracted_data = payload.get("extracted_data")
	if payload.get("telephony_data").get("duration") is not None:
		doc.call_duration = payload.get("telephony_data").get("duration")
	if payload.get("telephony_data").get("recording_url"):
		doc.recording_url = payload.get("telephony_data").get("recording_url")
	

	doc.save(ignore_permissions=True)


def create_bolna_call_for_incoming(payload,campaign):
	lead = frappe.get_doc("CRM Lead", {"mobile_no": payload.get("contact_number"), "custom_campaign": campaign})
	
	frappe.get_doc({
		"doctype": "Bolna Call",
		"execution_id": payload.get("execution_id"),
		"lead": lead.name,
		"call_type": "Incoming",
		"status": "queued",
		"bolna_agent": payload.get("agent_id"),
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return lead

def update_lead_bolna_status(status, lead_name):
	
	lead = frappe.get_doc("CRM Lead", lead_name)
	lead.custom_bolna_status = status
	lead.save(ignore_permissions=True)
