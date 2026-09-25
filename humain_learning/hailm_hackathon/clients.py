"""Outbound clients: the HAILM LMS (discount codes) and AiSensy (WhatsApp).

All credentials come from site_config.json — nothing is hard-coded.
"""

import frappe
import requests

from .utils import build_aisensy_payload, build_discount_code_payload, generate_code

TIMEOUT = 30
DEFAULT_LMS_API_BASE = "https://api.staging.ailiteracymission.org/api/v1"
AISENSY_URL = "https://backend.aisensy.com/campaign/t1/api/v2"


class ConfigMissing(Exception):
	"""A required site_config key is not set. Fulfilment records this and stops cleanly."""


def _conf(key, default=None, required=False):
	value = frappe.conf.get(key, default)
	if required and not value:
		raise ConfigMissing(f"site_config key '{key}' is not set")
	return value


def lms_api_base():
	return _conf("hailm_lms_api_base", DEFAULT_LMS_API_BASE).rstrip("/")


def _lms_token():
	resp = requests.post(
		f"{lms_api_base()}/auth/login",
		json={
			"identifier": _conf("hailm_lms_identifier", required=True),
			"password": _conf("hailm_lms_password", required=True),
		},
		timeout=TIMEOUT,
	)
	resp.raise_for_status()
	token = (resp.json().get("data") or {}).get("accessToken")
	if not token:
		raise RuntimeError("LMS login returned no access token")
	return token


def create_lms_discount_code(student_name, registration_name, max_attempts=3):
	"""Create a single-use, 100% olympiad code on the LMS. Returns (code, lms_id).

	Retries with a fresh code if the LMS rejects one as a duplicate.
	"""
	token = _lms_token()
	headers = {"Authorization": f"Bearer {token}"}
	package_ids = _conf("hailm_hackathon_package_ids") or None
	ends_at = _conf("hailm_hackathon_code_ends_at") or None

	last_error = None
	for _ in range(max_attempts):
		code = generate_code()
		payload = build_discount_code_payload(
			code, student_name, registration_name, ends_at=ends_at, package_ids=package_ids
		)
		resp = requests.post(
			f"{lms_api_base()}/payments/discount-codes", json=payload, headers=headers, timeout=TIMEOUT
		)
		if resp.status_code in (200, 201):
			body = resp.json()
			doc = body.get("data", body) if isinstance(body, dict) else {}
			return doc.get("code", code), doc.get("_id")
		last_error = f"{resp.status_code}: {resp.text[:300]}"
		if resp.status_code != 409 and "exist" not in resp.text.lower():
			break  # not a duplicate-code clash, retrying with a new code will not help
	raise RuntimeError(f"LMS discount code creation failed: {last_error}")


def aisensy_configured():
	return bool(_conf("aisensy_api_key") and _conf("aisensy_hailm_campaign_name"))


def send_aisensy_whatsapp(mobile, first_name, values):
	"""Send the post-payment WhatsApp. Returns the raw response text for the audit trail."""
	param_order = _conf("aisensy_hailm_template_params") or ["name", "code"]
	payload = build_aisensy_payload(
		api_key=_conf("aisensy_api_key", required=True),
		campaign_name=_conf("aisensy_hailm_campaign_name", required=True),
		mobile=mobile,
		first_name=first_name,
		values=values,
		param_order=param_order,
	)
	resp = requests.post(AISENSY_URL, json=payload, timeout=TIMEOUT)
	if resp.status_code >= 400:
		raise RuntimeError(f"AiSensy {resp.status_code}: {resp.text[:300]}")
	return resp.text[:1000]
