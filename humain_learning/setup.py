import frappe
import json
from .bolna.services import sync_bolna_agents
def populate_bolna_call_status():
	statuses = [
		'rescheduled',
		'cancelled',
		'stopped',
		'balance-low',
		'completed',
		'call-disconnected',
		'in-progress',
		'ringing',
		'initiated',
		'scheduled',
		'queued',
		'busy',
		'error',
		'failed',
		'no-answer'
	]

	for status in statuses:
		if not frappe.db.exists("Bolna Call Status", status):
			frappe.get_doc({
				"doctype": "Bolna Call Status",
				"id": status
			}).insert(ignore_permissions=True)

	frappe.db.commit()

def setup_bolna_retry_config():
    config = frappe.get_doc("Bolna Retry Config")
    max_retries = 3
    intervals = [11, 11, 11]
    statuses = ["failed", "busy", "error", "no-answer"]

    intervals_json = json.dumps(intervals, separators=(",", ":"))

    config.enabled = 1
    config.retry_on_voicemail = 1
    config.max_retries = max_retries
    config.retry_interval_minutes = intervals_json

    config.set("retry_on_statuses", [])
    for s in statuses:
        config.append("retry_on_statuses", {"status": s})

    config.save(ignore_permissions=True)
    frappe.db.commit()

def after_install():
	populate_bolna_call_status()
	setup_bolna_retry_config()
	sync_bolna_agents()