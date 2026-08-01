import frappe
import json
from ..bolna.services import sync_bolna_agents

def ensure_default_marketing_campaigns():
	"""Idempotently create Marketing Campaign records that lead_controller.py
	relies on existing (e.g. the fallback 'Organic' campaign). Safe to call
	repeatedly - on install, on migrate, or lazily from business logic."""
	default_campaigns = ["Organic"]

	for campaign_name in default_campaigns:
		if not frappe.db.exists("Marketing Campaign", campaign_name):
			frappe.get_doc({
				"doctype": "Marketing Campaign",
				"name": campaign_name,
				"campaign_description": ""
			}).insert(ignore_permissions=True, ignore_if_duplicate=True)

	frappe.db.commit()

def ensure_master_data():
	"""Idempotent seeding of all master data this app's business logic
	assumes exists. Called on both after_install and after_migrate so it
	self-heals sites that were restored/migrated without ever running
	after_install (e.g. backups taken before these defaults existed)."""
	populate_bolna_call_status()
	ensure_default_marketing_campaigns()

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
	intervals = [120, 120, 120]
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

def setup_meta_event_names():
	event_names = [
		"Contact",
		"QualifiedLead",
		"Purchase"
	]

def after_install():
	ensure_master_data()
	setup_bolna_retry_config()
	try:
		sync_bolna_agents()
	except Exception:
		frappe.log_error(title="after_install: sync_bolna_agents failed")

def after_migrate():
	ensure_master_data()