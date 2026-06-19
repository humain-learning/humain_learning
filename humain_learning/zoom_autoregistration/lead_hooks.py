import frappe
from humain_learning.zoom_autoregistration.api import register_to_webinar,_retry_failed_registration
from frappe.utils import get_datetime, getdate

def register_lead_to_webinar(lead,_):
    if lead.custom_actionable != "Webinar":
        return
    if lead.custom_registered_for_webinar:
        return

    if lead.facebook_form_id:
        webinar = frappe.db.get_value("Campaign Purpose", {"parent": lead.custom_campaign, "form_id": lead.facebook_form_id }, "webinar")
    else: 
        webinar = frappe.db.get_value("Campaign Purpose", {"parent": lead.custom_campaign, "action":lead.custom_actionable}, "webinar")    

    if not webinar:
        failure = frappe.get_doc({
            "doctype": "Failed Registration",
            "lead": lead.name,
            "webinar": None,
            "http_code": None,
            "error_code": None,
            "facebook_form_id": lead.facebook_form_id,
            "message": "No webinar found",
            "last_attempt_at": frappe.utils.now_datetime()
        })
        failure.insert(ignore_permissions=True)
        frappe.db.commit()
        return
    webinar_doc = frappe.get_doc("Zoom Webinar", webinar)
    frappe.enqueue(
        register_to_webinar,
        lead=lead.name,
        webinar=webinar_doc.name,
        queue="short",
        timeout=30,
        enqueue_after_commit=True
    )


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

