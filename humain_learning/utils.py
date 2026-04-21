from frappe.utils import get_datetime, convert_utc_to_system_timezone


def system_datetime(dt):
	return convert_utc_to_system_timezone(get_datetime(dt)).replace(tzinfo=None)
