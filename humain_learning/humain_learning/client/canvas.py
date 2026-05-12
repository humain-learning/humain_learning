# LIST OF FUNCTIONS THAT INTERACT WITH CANVAS LMS


import frappe
import requests
from frappe.utils import get_datetime
from zoneinfo import ZoneInfo

CANVAS_BASE_URL = "https://lms.humainlearning.ai/api/v1"
tz = ZoneInfo(frappe.get_system_settings("time_zone"))

@frappe.whitelist()
def get_single_course_details(course_id,template: bool):
    token_doc = frappe.get_single("Canvas Admin Token")
    
    if not token_doc.token:
        frappe.throw("Please set the Canvas API token and URL in the Canvas Admin Token doctype.")
        
    headers = {
        "Authorization": f"Bearer {token_doc.get_password('token')}"
    }
    
    response = requests.get(f"{CANVAS_BASE_URL}/courses/{course_id}", headers=headers)
    
    if response.status_code != 200:
        frappe.throw(f"Failed to fetch course details: {response.text}")
    if response.status_code == 404:
        frappe.throw("Course not found. Please check the course ID.")
    
    
    data = response.json()
    
    if template:
        if not data.get('template'):
            frappe.throw("This course is not a template course. Please provide a template course ID.")
        else:
            return {
                "course_name": data.get("name"),
                "course_code": data.get("course_code"),
                "sub_account": data.get('account_id'),
                "state": data.get('workflow_state').capitalize(),
            }

    if not template:
        if data.get('template'):
            frappe.throw("This course is a template course. Please provide a non-template course ID.")
        else:
            start_at = get_datetime(data.get("start_at")).astimezone(tz).replace(tzinfo=None)
            end_at = get_datetime(data.get("end_at")).astimezone(tz).replace(tzinfo=None)
            return {
                "course_name": data.get("name"),
                "course_code": data.get("course_code"),
                "sub_account": data.get('account_id'),
                "state": data.get('workflow_state').capitalize(),
                "start_date": start_at,
                "end_date": end_at,
            }