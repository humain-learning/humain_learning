from zoneinfo import ZoneInfo
import frappe
from frappe.utils import get_datetime,now_datetime
import requests
from .utils import extract_error

ZOOM_BASE_URL = "https://api.zoom.us/v2"

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

    # Success path
    tz = ZoneInfo(frappe.get_system_settings("time_zone"))

    start_time = get_datetime(data.get("start_time")).astimezone(tz).replace(tzinfo=None)

    created_at = get_datetime(data.get("created_at")).astimezone(tz).replace(tzinfo=None)

    return {
        "topic": data.get("topic"),
        "start_time": start_time,
        "created_at": created_at,
        "host_email": data.get("host_email"),
    }
    
    

def register_to_webinar(lead,webinar):
    
    lead = frappe.get_doc("CRM Lead", lead)
    token_doc = frappe.get_single("Zoom OAuth Token")
    webinar = frappe.get_doc("Zoom Webinar", webinar)
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
        frappe.db.set_value("CRM Lead", lead.name, "custom_registered_for_webinar", 1)
        
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