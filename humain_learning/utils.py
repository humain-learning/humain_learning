from frappe.utils import get_datetime
def system_datetime(dt):
	return get_datetime(dt).replace(tzinfo=None)
