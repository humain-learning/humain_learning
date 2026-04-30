import requests
import frappe
from .utils import build_retry_config
BOLNA_BASE_URL = "https://api.bolna.ai/"
ALLOWED_BOLNA_SOURCES = ["13.203.39.153"]
# ALLOWED_BOLNA_SOURCES = []

def bolna_headers():
	return {
		"Authorization": f"Bearer {frappe.get_single('Bolna Credentials').get_password('access_token')}"
	}

def get_all_agents():
	url = f"{BOLNA_BASE_URL}/v2/agent/all"
	
	headers = bolna_headers()

	response = requests.get(url, headers=headers)

	if response.status_code == 403:
		frappe.throw("Invalid Credentials, please check Bolna Credentials")
	if response.status_code != 200:
		frappe.throw(f"Failed to fetch agents: {response.text}")
	if response.status_code == 200:
		# frappe.msgprint(response.json())
		return response.json()

def get_all_phones():
	url = f"{BOLNA_BASE_URL}/phone-numbers/all"
	
	headers = bolna_headers()

	response = requests.get(url, headers=headers)

	if response.status_code == 403:
		frappe.throw("Invalid Credentials, please check Bolna Credentials")
	if response.status_code != 200:
		frappe.throw(f"Failed to fetch phones: {response.text}")
	if response.status_code == 200:
		return response.json()
		
	
def trigger_call(lead_name,campaign_name,retry):
	lead = frappe.get_doc("CRM Lead", lead_name)
	campaign = frappe.get_doc("Marketing Campaign", campaign_name)

	agent_id = campaign.custom_outgoing_agent
	from_phone = frappe.get_doc("Bolna Phone").phone_no
	recipient_phone = lead.mobile_no

	url = f"{BOLNA_BASE_URL}/call"
	headers = {
		**bolna_headers(),
		"Content-Type": "application/json"
	}
	if retry:
		retry_config = build_retry_config()
	
		payload = {
			"agent_id": agent_id,
			"recipient_phone_number": recipient_phone,
			"from_phone_number": from_phone,
			"user_data":{
				"name": lead.lead_name
			},
			"retry_config": retry_config
		}
	else:
		payload = {
			"agent_id": agent_id,
			"recipient_phone_number": recipient_phone,
			"from_phone_number": from_phone,
			"user_data":{
				"name": lead.lead_name
			}
		}

	response = requests.post(url, json=payload, headers=headers)
	return response.json()