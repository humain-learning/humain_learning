import frappe

def assign_campaign(lead,_):
    if lead.facebook_form_id:
        campaign = frappe.db.get_value("Campaign Purpose", {"form_id": lead.facebook_form_id},["parent","action"], as_dict=True)
        if campaign:
            lead.custom_campaign = campaign.parent
            lead.custom_actionable = campaign.action
        else: 
            return
    elif lead.custom_utm_campaign:
        campaign_name = lead.custom_utm_campaign.strip()

        if frappe.db.exists("Marketing Campaign", campaign_name):
            lead.custom_campaign = campaign_name
        else:
            frappe.get_doc({
                "doctype": "Marketing Campaign",
                "name": campaign_name,
                "campaign_description": ""
            }).insert(ignore_permissions=True, ignore_if_duplicate=True)
            lead.custom_campaign = campaign_name
    

def standardize_mobile(doc, _):
    if not doc.mobile_no:
        return
    default_country_code = '+91'
    digits = ''.join(filter(str.isdigit, doc.mobile_no))
    
    if len(digits) == 12 and digits.startswith('91'):
        doc.mobile_no = '+' + digits
    elif len(digits) == 10:
        doc.mobile_no = default_country_code + digits
    elif len(digits) == 11 and digits.startswith('0'):
        doc.mobile_no = default_country_code + digits[1:]
    else:
        return
    