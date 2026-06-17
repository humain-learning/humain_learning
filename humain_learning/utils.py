from zoneinfo import ZoneInfo
from frappe.utils import get_datetime, convert_utc_to_system_timezone, get_system_timezone
from frappe.utils import add_to_date, format_date, format_time, getdate
import frappe

ist = ZoneInfo("Asia/Kolkata")
utc = ZoneInfo("UTC")

def utc_to_sys_dt(dt):
	return convert_utc_to_system_timezone(get_datetime(dt)).replace(tzinfo=None)


def sys_dt_to_utc(dt):
	systz = ZoneInfo(get_system_timezone())
	return get_datetime(dt).replace(tzinfo=systz).astimezone(utc).isoformat()


def convert_to_ordinal_timing(start_time, duration):
	start_time_obj = get_datetime(f"2000-01-01 {start_time}")
	end_time_obj = add_to_date(start_time_obj, seconds=duration, as_datetime=True)

	start_label = format_time(start_time_obj, "h a").replace(" ", "").upper()
	end_label = format_time(end_time_obj, "h a").replace(" ", "").upper()
	return f"{start_label}-{end_label}"

def convert_to_ordinal_date(date):
	date_obj = getdate(date)
	day = date_obj.day

	if 11 <= day % 100 <= 13:
		suffix = "th"
	else:
		suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

	return f"{day}{suffix} {format_date(date_obj, 'MMM')}"


def validate_required_fields(required_fields, payload):
	missing_fields = [
		field
		for field in required_fields
		if payload.get(field) is None
	]

	if missing_fields:
		frappe.throw(
			f"Missing required fields: {', '.join(missing_fields)}"
		)
	else:
		return True