import frappe
import ipaddress

def _client_ip():
	xff = frappe.get_request_header("X-Forwarded-For")
	if xff:
		return xff.split(",")[0].strip()
	return (frappe.request.remote_addr or "").strip()


def _ip_allowed(ip_str, ALLOWED_BOLNA_SOURCES):
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

def build_retry_config():
	config = frappe.get_single("Bolna Retry Config")
	if not config.enabled:
		return None
	
	else: 
		return {
		"enabled": True,
		"max_retries": config.max_retries,
		"retry_on_statuses": config.get_retry_statuses(),
		"retry_intervals_minutes": config.get_intervals(),
		"retry_on_voicemail": True if config.retry_on_voicemail else False
		}