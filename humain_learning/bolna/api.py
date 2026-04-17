import requests
import frappe
import ipaddress
import json
from .utils import update_bolna_call_record, create_bolna_call_for_incoming
BOLNA_BASE_URL = "https://api.bolna.ai/"
# ALLOWED_BOLNA_SOURCES = ["13.203.39.153"]
ALLOWED_BOLNA_SOURCES = []

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
		
	
def trigger_call(lead_name,campaign_name):
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
	retry_config = {
		"enabled": True,
		"max_retries": 3,
		"retry_on_statuses": ["no-answer", "failed", "busy", "error"],
		"retry_intervals_minutes": [15,15,15],
		"retry_on_voicemail": False
	}
	payload = {
		"agent_id": agent_id,
		"recipient_phone_number": recipient_phone,
		"from_phone_number": from_phone,
		"user_data":{
			"name": lead.lead_name
		},
		"retry_config": retry_config
	}

	response = requests.post(url, json=payload, headers=headers)
	print(response.request.body)
	return response.json()


def _client_ip():
	xff = frappe.get_request_header("X-Forwarded-For")
	if xff:
		return xff.split(",")[0].strip()
	return (frappe.request.remote_addr or "").strip()


def _ip_allowed(ip_str):
	if not ALLOWED_BOLNA_SOURCES:
		return True

	try:
		ip_obj = ipaddress.ip_address(ip_str)
	except ValueError:
		return False

	for rule in ALLOWED_BOLNA_SOURCES:
		try:
			if "/" in rule:
				if ip_obj in ipaddress.ip_network(rule, strict=False):
					return True
			else:
				if ip_obj == ipaddress.ip_address(rule):
					return True
		except ValueError:
			continue

	return False


@frappe.whitelist(allow_guest=True)
def bolna_webhook():
	if frappe.request.method != "POST":
		frappe.response.http_status_code = 405
		return {"status": "error", "message": "Method not allowed"}

	client_ip = _client_ip()
	if not _ip_allowed(client_ip):
		frappe.response.http_status_code = 403
		return {"status": "error", "message": "Forbidden"}

	payload = frappe.form_dict

	execution_id = payload.get("id")

	frappe.logger("bolna").info(
		"Webhook received | execution_id=%s | keys=%s",
		execution_id,
		sorted(payload.keys()) if isinstance(payload, dict) else []
	)

	if not execution_id:
		frappe.response.http_status_code = 400
		return {
			"status": "error",
			"message": "Missing execution_id",
			"received_keys": sorted(payload.keys()) if isinstance(payload, dict) else []
		}

	if not frappe.db.exists("Bolna Call", execution_id):
		frappe.logger("bolna").warning("No Bolna Call found for execution_id=%s", execution_id)
		return {"status": "ok", "message": f"No Bolna Call found for {execution_id}"}

	update_bolna_call_record(payload)
	
	return {"status": "success", "execution_id": execution_id}

@frappe.whitelist()
def send_user_data():
	if frappe.request.method != "GET":
		frappe.response.http_status_code = 405
		return {"status": "error", "message": "Method not allowed"}
	
	payload = frappe.form_dict
	campaign = frappe.db.get_value("Marketing Campaign", {"custom_bolna_enabled": 1,"custom_incoming_agent":payload.get("agent_id")}, "name")
	lead = create_bolna_call_for_incoming(payload,campaign)

	frappe.response["name"] = lead.name
	return
