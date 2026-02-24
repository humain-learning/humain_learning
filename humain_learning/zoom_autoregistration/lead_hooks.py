import frappe
from humain_learning.zoom_autoregistration.api import register_to_webinar,_retry_failed_registration

    
def register_lead_to_webinar(lead,_):
    if lead.custom_actionable != "Webinar":
        return
    if lead.custom_registered_for_webinar:
        return
    if not lead.facebook_form_id:
        return 
    
    webinar = frappe.db.get_value("Webinar Mapping", {"form_id": lead.facebook_form_id},"webinar")
    
    if not webinar:
        failure = frappe.get_doc({
            "doctype": "Failed Registration",
            "lead": lead.name,
            "webinar": None,
            "http_code": None,
            "error_code": None,
            "facebook_form_id": lead.facebook_form_id,
            "message": "No webinar mapping found for the lead's Facebook Form ID.",
            "last_attempt_at": frappe.utils.now_datetime()
        })
        failure.insert(ignore_permissions=True)
        return
    frappe.enqueue(register_to_webinar, lead=lead.name, webinar=webinar, queue="short", timeout=30)



@frappe.whitelist()   
def retry_failed_registration(lead,webinar):
    frappe.enqueue(
        _retry_failed_registration,
        lead=lead,
        webinar=webinar,
        queue="short",
        timeout=30
    )
    # _retry_failed_registration(lead,webinar_id)