import frappe

def create_crm_notification(notification):
	doc = frappe.get_doc({
		"doctype": "CRM Notification",
		**notification
	}).insert(ignore_permissions=True, ignore_if_duplicate=True)
	print("CRM Notification created successfully for lead:", notification.get("reference_name"))
	return


def new_hot_lead(lead, _):
	if lead.has_value_changed("custom_intent") and lead.custom_intent == "Hot":
		print("New hot lead identified:", lead.name)
		from_user = frappe.session.user
		print(from_user)
		notification = {
			"from_user": from_user,
			"to_user": lead.lead_owner,
			"type": "Task",
			"message": f"New hot lead: {lead.lead_name}({lead.name}). Please follow up as soon as possible.",
			"notification_text": f'<div class="mb-2 leading-5 text-ink-gray-5"><span class="font-medium text-ink-gray-9">Bolna</span> <span>identified a new hot lead <span class="font-medium text-ink-gray-9">{lead.lead_name} ({lead.name})</span>. Please follow up as soon as possible.</span></div>',
			"reference_doctype": "CRM Lead",
			"reference_name": lead.name,
			"notification_type_doctype": "CRM Lead",
   			"notification_type_doc": lead.name,
		}
		print("Creating CRM Notification for new hot lead\n",notification)
		create_crm_notification(notification)
	else:
		pass