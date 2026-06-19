import frappe
from frappe.utils import now_datetime, add_to_date




def get_webinars_for_attendance():

	threshold_time = add_to_date(now_datetime(), minutes=-55)
	webinars = frappe.get_all("Zoom Webinar", filters={"end_time": ("<=", threshold_time),"attendance_processed":0}, pluck='name')

	for webinar in webinars:
		frappe.enqueue(
			"humain_learning.humain_learning.zoom_autoregistration.webinar_attendance", webinar=webinar
			)