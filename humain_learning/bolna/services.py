import frappe
from .api import *


@frappe.whitelist()
def sync_bolna_phone():
	phone = frappe.parse_json(get_all_phones()[0])

	doc = frappe.get_doc("Bolna Phone")
	doc.id = phone.id
	doc.phone_no = phone.phone_number
	doc.provider = phone.telephony_provider.capitalize()
	doc.save(ignore_permissions=True)

@frappe.whitelist()
def sync_bolna_agents():

	agents = frappe.parse_json(get_all_agents())

	if len(agents) == 0:
		return 0
	new_agents = 0
	for agent in agents:
		agent = frappe.parse_json(agent)
		if frappe.db.exists("Bolna Agent", agent.id):
			doc = frappe.get_doc("Bolna Agent", agent.id)
			doc.agent_name = agent.agent_name
			doc.save(ignore_permissions=True)
		else:
			frappe.get_doc({
				"doctype": "Bolna Agent",
				"agent_id": agent.id,
				"agent_name": agent.agent_name,
				"created_at": agent.created_at.replace("T", " ")
			}).insert(ignore_permissions=True)
			new_agents += 1
	return new_agents


def process_extractions(call_doc):
	if type(call_doc) == str:
		call_doc = frappe.get_doc("Bolna Call", call_doc)

	extracted_data = frappe.parse_json(call_doc.extracted_data)

	lead = frappe.get_doc("CRM Lead", call_doc.lead)

	extraction_dict = extractions_to_dict(extracted_data, call_doc.bolna_agent)

	for key, value in extraction_dict.items():
		if value is not None:
			if key == "Lead Intent":
				lead.custom_intent = value
		
	lead.save(ignore_permissions=True)


def extractions_to_dict(extracted_data, agent):
	extracted_dict = {}
	agent = frappe.get_doc("Bolna Agent", agent)

	for row in agent.extractions:
		section_data = extracted_data.get(row.section) or {}
		if row.extraction not in section_data:
			extracted_dict[row.extraction] = None
			frappe.log_error(
				title="Bolna Extraction Error",
				message=(
					f"Missing extraction '{row.extraction}' under section '{row.section}' "
					f"in extracted_data from Agent {agent.agent_name}. "
					"This likely indicates external service configuration mismatch."
				)
			)
			continue

		extraction_data = section_data.get(row.extraction) or {}
		objective = extraction_data.get("objective")
		if objective is None:
			extracted_dict[row.extraction] = None
			frappe.log_error(
				title="Bolna Extraction Error",
				message=(
					f"Missing objective for extraction '{row.extraction}' under section "
					f"'{row.section}' in extracted_data from Agent {agent.agent_name}."
				),
			)
			continue

		extracted_dict[row.extraction] = objective
		
	return extracted_dict

def update_lead_status(call_doc):
	lead = frappe.get_doc("CRM Lead", call_doc.lead)

	lead.custom_bolna_call_status = call_doc.status
	lead.save(ignore_permissions=True)

def add_comment_to_lead(call_doc):
	
	frappe.get_doc({
		"doctype": "Comment",
		"comment_type": "Info",
		"reference_doctype": "CRM Lead",
		"reference_name": call_doc.lead,
		"content": f"Bolna Call Summary - {call_doc.summary}",
		"comment_by": f"Bolna Agent - {call_doc.bolna_agent}",
		"comment_email": "bolna@system.local"
	}).insert(ignore_permissions=True)