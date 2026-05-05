import frappe
from .client import trigger_call
from frappe.utils import now_datetime

def call_via_agent(lead,method,retry=True):
	if not lead.custom_campaign:
		return None
	campaign = frappe.get_doc("Marketing Campaign",lead.custom_campaign)
	if not campaign:
		return None
	if not campaign.custom_bolna_enabled:
		frappe.logger("bolna").warning(f"Campaign {campaign.name} is not enabled for Bolna. Skipping call trigger for lead {lead.name}.")
		return None
	if not campaign.custom_outgoing_agent:
		frappe.logger("bolna").warning(f"Campaign {campaign.name} is enabled for Bolna but no outgoing agent is set. Skipping call trigger for lead {lead.name}.")
		return None

	bolna_call = trigger_call(lead.name,lead.custom_campaign,retry=retry)

	if bolna_call.get("execution_id"):
		lead.custom_bolna_exec_id = bolna_call.get("execution_id")
		lead.save(ignore_permissions=True)

	if not bolna_call.get("execution_id"):
		frappe.log_error(f"Failed to trigger call for lead {lead.name} via Bolna. Response: {bolna_call}")
		return None
	

	frappe.get_doc({
		"doctype": "Bolna Call",
		"execution_id": bolna_call.get("execution_id"),
		"lead": lead.name,
		"recipient_no": lead.mobile_no,
		"status": bolna_call.get("status"),
		"bolna_agent": campaign.custom_outgoing_agent,
		"call_type": "Outgoing",
		"last_updated_at": now_datetime()
	}).insert(ignore_permissions=True)

	return bolna_call.get("execution_id")



@frappe.whitelist()
def retry_bolna_lifecycle_bulk(leads):
	leads = frappe.parse_json(leads) if isinstance(leads, str) else leads
	leads = leads or []

	result = {
		"total": len(leads),
		"succeeded": 0,
		"failed": 0,
		"failedinside": 0,
		"failed_leads": [],
	}

	for lead_name in leads:
		try:
			lead = frappe.get_doc("CRM Lead", lead_name)
			execution_id = call_via_agent(lead, None,retry=False)
			if execution_id:
				result["succeeded"] += 1
			else:
				result["failedinside"] += 1
				result["failed_leads"].append(lead_name)
		except Exception:
			frappe.log_error(frappe.get_traceback(), f"Bolna bulk retry failed for {lead_name}")
			result["failed"] += 1
			result["failed_leads"].append(lead_name)

	return result