import frappe
from .client import trigger_call
from frappe.utils import now_datetime

def call_via_agent(lead,_):

	campaign = frappe.get_doc("Marketing Campaign",lead.custom_campaign)
	if not campaign:
		return
	if not campaign.custom_bolna_enabled:
		return
	if not campaign.custom_outgoing_agent:
		return

	bolna_call = trigger_call(lead.name,lead.custom_campaign)

	if bolna_call.get("execution_id"):
		lead.custom_bolna_exec_id = bolna_call.get("execution_id")
		lead.save(ignore_permissions=True)

	if not bolna_call.get("execution_id"):
		frappe.log_error(f"Failed to trigger call for lead {lead.name} via Bolna. Response: {bolna_call}")
		return
	

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