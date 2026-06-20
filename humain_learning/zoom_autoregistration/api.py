from zoneinfo import ZoneInfo
import frappe
from frappe.utils import cint, get_datetime,now_datetime,getdate
import requests
from .utils import extract_error
from datetime import timedelta
from humain_learning.utils import utc_to_sys_dt, sys_dt_to_utc
import sys
ZOOM_BASE_URL = "https://api.zoom.us/v2"

frappe.utils.logger.set_log_level("DEBUG")
logger = frappe.logger("zoom", with_more_info=True, allow_site=True, file_count=50, max_size=10485760)  # 10MB



@frappe.whitelist()
def fetch_webinar(webinar_id):

	if not webinar_id:
		frappe.throw("Please provide a Webinar ID.")

	webinar_id = webinar_id.replace(" ", "")
	token_doc = frappe.get_single("Zoom OAuth Token")

	url = f"{ZOOM_BASE_URL}/webinars/{webinar_id}"
	headers = {
		"Authorization": f"{token_doc.token_type} {token_doc.get_password('access_token')}"
	}

	# Network safety
	try:
		response = requests.get(url, headers=headers, timeout=10)
	except requests.exceptions.RequestException as e:
		frappe.throw(str(e))

	# Attempt JSON parse safely
	try:
		data = response.json()
	except ValueError:
		# Not JSON → extract structured or raw error
		status_code, err_code, err_msg = extract_error(response)
		frappe.throw(err_msg or "Unexpected response from Zoom.")

	# Handle non-success responses
	if response.status_code != 200:

		err_code = data.get("code")
		err_msg = data.get("message", "No message provided")

		if err_code == 300:
			frappe.throw("Webinar ID is invalid. Please check Webinar ID and try again.")

		elif err_code == 200:
			frappe.throw("Account is not subscribed to the Webinar Plan.")

		elif response.status_code == 404:
			frappe.throw("Webinar does not exist. Please check Webinar ID and try again.")

		elif response.status_code == 429:
			frappe.throw("Too many requests. Please try again later.")

		elif response.status_code == 401:
			frappe.throw(err_msg or "Unauthorized. Please check credentials.")

		frappe.throw(f"Zoom Error: {err_msg}")

	start_time = utc_to_sys_dt(data.get("start_time"))

	created_at = utc_to_sys_dt(data.get("created_at"))
	 
	return {
		"topic": data.get("topic"),
		"start_time": start_time,
		"created_at": created_at,
		"end_time": start_time + timedelta(minutes=data.get("duration", 0)),
		"host_email": data.get("host_email"),
	}
	
	

@frappe.whitelist()
def register_to_webinar(lead,webinar):
	
	lead = frappe.get_doc("CRM Lead", lead)
	token_doc = frappe.get_cached_doc("Zoom OAuth Token")
	webinar = frappe.get_doc("Zoom Webinar", webinar)
	webinar_id = webinar.webinar_id.replace(" ", "")
	lead.reload()
	url = f"{ZOOM_BASE_URL}/webinars/{webinar_id}/registrants"
	
	headers = {
		"Authorization": f"{token_doc.token_type} {token_doc.get_password('access_token')}",
		"Content-Type": "application/json"
	}
	
	payload = {
		"email": lead.email.strip(),
		"first_name": lead.first_name,
		"last_name": lead.last_name if lead.last_name else "",
		"phone": lead.mobile_no,
	}
	try:
		r = requests.post(url, json=payload, headers=headers, timeout=30)
		
	except requests.exceptions.RequestException as e:
		failed = frappe.get_doc({
			"doctype": "Failed Registration",
			"lead": lead.name,
			"webinar": webinar.name,
			"http_code": None,
			"error_code": None,
			"message": str(e),
			"last_attempt_at": now_datetime()
		})
		failed.insert(ignore_permissions=True)
		return

	if r.status_code ==201:
		lead.custom_registered_for_webinar = 1
		next_idx = (
			frappe.db.count(
				"Webinar Registrant",
				filters={
					"parent": webinar.name,
					"parenttype": "Zoom Webinar",
					"parentfield": "registrants",
				},
			)
			+ 1
		)
		data=r.json()
		frappe.get_doc({
			"doctype": "Webinar Registrant",
			"parent": webinar.name,
			"parenttype": "Zoom Webinar",
			"parentfield": "registrants",
			"idx": next_idx,
			"registrant": lead.name,
			"registrant_id": data.get("registrant_id"),
			"registered_on": frappe.utils.now_datetime(),
			"join_url": data.get("join_url")
		}).insert(ignore_permissions=True)

		dt = get_datetime(webinar.start_time)
		time_str = dt.strftime("%-I:%M%p") if dt.minute != 0 else dt.strftime("%-I%p")
		lead.custom_webinar = webinar.name
		lead.custom_webinar_time = time_str
		lead.custom_webinar_date = getdate(webinar.start_time)
		lead.custom_webinar_start_time = webinar.start_time
		lead.save()
		return
	
	else:
		status_code, err_code, err_msg = extract_error(r)
		failed = frappe.get_doc({
			"doctype": "Failed Registration",
			"lead": lead.name,
			"webinar": webinar.name,
			"http_code": status_code,
			"error_code": err_code,
			"message": err_msg,
			"last_attempt_at": now_datetime()
		})
		failed.insert(ignore_permissions=True)
		return


def _retry_failed_registration(lead,webinar):
	
	lead = frappe.get_doc("CRM Lead", lead)
	
	webinar = frappe.get_doc("Zoom Webinar", webinar)
	
	token_doc = frappe.get_single("Zoom OAuth Token")
	
	webinar_id = webinar.webinar_id.replace(" ", "")
	
	url = f"{ZOOM_BASE_URL}/webinars/{webinar_id}/registrants"
	
	headers = {
		"Authorization": f"{token_doc.token_type} {token_doc.get_password('access_token')}",
		"Content-Type": "application/json"
	}
		
	payload = {
		"email": lead.email.strip(),
		"first_name": lead.first_name,
		"last_name": lead.last_name if lead.last_name else "",
		"phone": lead.mobile_no,
	}
	
	try:
		r = requests.post(url, json=payload, headers=headers, timeout=30)
		
	except requests.exceptions.RequestException as e:
		frappe.db.set_value(
			"Failed Registration",
			{"lead": lead.name, "webinar": webinar.name},
			{    
				"http_code": None,
				"error_code": None,
				"message": str(e),
				"last_attempt_at": now_datetime()
			}
		)
		
		return
		
	if r.status_code ==201:
		frappe.db.set_value("CRM Lead", lead.name, "custom_registered_for_webinar", 1)
		frappe.db.delete("Failed Registration", {"lead": lead.name, "webinar": webinar.name})
		
		return
	else:
		status_code, err_code, err_msg = extract_error(r)
		frappe.db.set_value(
			"Failed Registration",
			{"lead": lead.name, "webinar": webinar.name},
			{
				"http_code": status_code,
				"error_code": err_code,
				"message": err_msg,
				"last_attempt_at": now_datetime()
			}
		)
		
		return


def shorten_url(registrant):
	access_key = frappe.get_cached_doc("URL Shortner Credentials").get_password("access_key")
	registrant = frappe.get_doc("Webinar Registrant", registrant)
	lead = frappe.get_doc("CRM Lead", registrant.registrant)
	expiry = frappe.db.get_value("Zoom Webinar", registrant.parent, "start_time") + timedelta(hours=1)
	join_url = registrant.join_url
	if not join_url:
		return
	if join_url.startswith("https://hlai.in"):
		return
	
	base_url = "https://hlai.in/api/developer/shorten-url"
	
	headers = {
		"Accept": "application/json",
		"Content-Type": "application/x-www-form-urlencoded",
		"X-API-KEY": access_key
	}
	
	payload = {
		"original_url": join_url,
		"expires_at": str(expiry)
	}
	
	response = requests.post(base_url, data=payload, headers=headers, timeout=30)
	if response.status_code != 200:
		frappe.log_error(f"URL Shortening failed")
		return
	
	data = response.json()
	
	registrant.db_set("join_url", data.get("shortened_url"))
	lead.db_set("custom_webinar_join_url", data.get("shortened_url"))


def _ordinal_suffix(day):
	if 11 <= day % 100 <= 13:
		return "th"
	return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


@frappe.whitelist()
def latest_webinar_details(template_id):
	webinars = frappe.get_all(
		"Zoom Webinar",
		filters={"template_course": str(template_id), "start_time": [">=", now_datetime()]},
		order_by="start_time desc",
		limit=1,
		fields=["start_time", "end_time"],
	)

	if not webinars:
		frappe.response.http_status_code = 404
		frappe.response.message = "No upcoming webinars found."
		return
	
	webinar = webinars[0]

	return {
		"start_time": sys_dt_to_utc(webinar.start_time),
		"end_time": sys_dt_to_utc(webinar.end_time),
	}


def fetch_attendee_list(webinar_id):
	already_processed = frappe.db.get_value("Zoom Webinar", webinar_id, "attendance_processed")
	if already_processed:
		logger.info(f"Attendance for webinar {webinar_id} has already been processed.")
		return
	
	webinar = frappe.get_doc("Zoom Webinar", webinar_id)
	webinar_id = webinar.name.replace(" ", "")
	url = f"{ZOOM_BASE_URL}/past_webinars/{webinar_id}/participants"
	token_doc = frappe.get_single("Zoom OAuth Token")
	headers = {
		"Authorization": f"{token_doc.token_type} {token_doc.get_password('access_token')}",
		"Content-Type": "application/json"
	}
	next_page_token = None
	participants = {}
	while True:
		params = {"page_size": 100}
		if next_page_token:
			params["next_page_token"] = next_page_token
		
		response = requests.get(url, headers=headers, params=params, timeout=30)

		if response.status_code != 200:
			logger.error(f"Failed to fetch attendees: {response.text}")
			break

		data = response.json()
		ps = data.get("participants")
		for p in ps:
			rid = p["registrant_id"]
			if rid not in participants.keys():
				participants[rid] = {
					"duration": p.get("duration", 0), 
				}
			else:
				participants[rid]["duration"] += p.get("duration", 0)

		next_page_token = data.get("next_page_token")
		if not next_page_token:
			break
	logger.info(f"Fetched {len(participants)} unique participants for webinar {webinar_id}.")
	if not participants:
		return

	rows = frappe.get_all(
		"Webinar Registrant",
		filters={"parent": webinar.name, "parenttype": "Zoom Webinar", "parentfield": "registrants", "registrant_id": ["in", list(participants.keys())]},
		fields=["name", "registrant_id", "registrant"],
	)
	logger.info(f"Found {len(rows)} matching registrants in ERP for webinar {webinar_id}.")
	for r in rows:
		duration = participants.get(r.registrant_id, {}).get("duration", 0)
		intent = "Hot" if duration >= 1800 else "Warm" if duration > 900 else "Cold"
		frappe.db.set_value("Webinar Registrant", r.name, {"attendee": 1, "view_time": duration})
		logger.info(f"Updated registrant {r.name} with duration {duration}.")
		frappe.db.set_value("CRM Lead", r.registrant, {"custom_attended_webinar": 1, "custom_intent": intent})
		logger.info(f"Updated lead {r.registrant} with attended_webinar=1 and intent={intent}.")
	webinar.attendance_processed = 1
	webinar.save()
	logger.info(f"Marked webinar {webinar_id} attendance as processed.")
	return


@frappe.whitelist()
def queue_attendance_fetch(webinar):
    frappe.enqueue(
        fetch_attendee_list,
        queue="long",
        webinar_id=webinar,
        timeout=1500,
    )

    return {"queued": True}