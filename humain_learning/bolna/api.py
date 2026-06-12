import requests
import frappe
import ipaddress
import json
from humain_learning.utils import sys_dt_to_utc
from .utils import _client_ip, _ip_allowed
from .services import update_bolna_call_record, create_bolna_call_for_incoming
ALLOWED_BOLNA_SOURCES = ["13.203.39.153"]
# ALLOWED_BOLNA_SOURCES = []



@frappe.whitelist(allow_guest=True)
def bolna_webhook():
	if frappe.request.method != "POST":
		frappe.response.http_status_code = 405
		return {"status": "error", "message": "Method not allowed"}

	client_ip = _client_ip()
	if not _ip_allowed(client_ip, ALLOWED_BOLNA_SOURCES):
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
		frappe.response.http_status_code = 404
		return {
			"status": "error",
			"message": f"No Bolna Call record found",
			"received_keys": sorted(payload.keys()) if isinstance(payload, dict) else []
		}
	
	last_update = frappe.db.get_value("Bolna Call", execution_id, "last_updated_at")

	if sys_dt_to_utc(last_update) >= payload.get("updated_at"):
		return {"status": "ok", "message": "Received older update. Ignoring."}
	
	update_bolna_call_record(payload)
	
	return {"status": "success"}



@frappe.whitelist()
def send_user_data():
	if frappe.request.method != "GET":
		frappe.response.http_status_code = 405
		return {"status": "error", "message": "Method not allowed"}
	
	payload = frappe.form_dict
	campaign = frappe.db.get_value("Marketing Campaign", {"custom_bolna_enabled": 1,"custom_incoming_agent":payload.get("agent_id")}, "name")
	lead = create_bolna_call_for_incoming(payload,campaign) #returns CRM Lead object

	frappe.response["name"] = lead.name
	return
