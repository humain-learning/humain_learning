#LIST OF METHODS THAT INTERACT WITH THE WEBSITE

import frappe
from ...utils import *
from frappe.utils import get_datetime
from werkzeug.exceptions import MethodNotAllowed

@frappe.whitelist()
def batch_details_of_template(template_id,start_date):
    if frappe.request.method != "GET":
        raise MethodNotAllowed(valid_methods=["GET"])
    
    batches = frappe.get_all(
        "Batch",
        filters={
            'template':template_id,
            'enabled':1,
            'start_date': [">",start_date]
        },
        order_by="start_date asc",
        pluck = "name"
        )
    
    response = []
    if not batches:
        return response
    
    for batchname in batches:
        batch = frappe.get_doc("Batch", batchname)
        response.append({
            'id': batch.name,
            'name': f'{batch.batch_name} Batch',
            'start_date': convert_to_ordinal_date(batch.start_date),
            'start_dto_bj': batch.start_date,
            'limited_seats': batch.limited_seats,
            'sold_out': batch.sold_out,
            'itinerary': [
                {
                    'date': convert_to_ordinal_date(row.date),
                    'date_obj'
                    'day': row.day,
                    'timing': (
                        "TBD" if row.time_tbd 
                        else convert_to_ordinal_timing(row.time, row.duration)
                    ) 
                    +
                    (
                        " - Graduation" if row.graduation 
                        else " - Doubt Clearing" if row.doubt_clearing 
                        else " - Orientation" if row.orientation 
                        else ""
                    )
                }
                for row in batch.itinerary
            ]
        })
    return response

@frappe.whitelist()
def current_active_discount(template_id):
    if frappe.request.method != "GET":
        raise MethodNotAllowed(valid_methods=["GET"])

    template_id = (template_id or "").strip()
    if not template_id:
        frappe.throw("template_id is required")

    web_discounts = frappe.get_all(
        "Web Discount",
        filters={
			"course": template_id,
			"enabled": 1,
        },
        fields=["name", "event"],
    )
    if not web_discounts:
        return {
            "template_id": template_id,
            "has_discount": False,
            "active_tier": None,
        }

    discount_names = [d.name for d in web_discounts]
    now = frappe.utils.now_datetime()
    active_tiers = frappe.get_all(
        "Discount Tier",
        filters={
            "parent": ["in", discount_names],
            "parenttype": "Web Discount",
            "start_datetime": ["<=", now],
            "end_datetime": [">", now],
        },
        fields=["parent", "start_datetime", "end_datetime", "discount_percent", "final_price"],
        order_by="start_datetime desc",
        limit_page_length=1,
    )

    if not active_tiers:
        base_price = frappe.db.get_value("Template Course", template_id, "price")
        return {
            "template_id": template_id,
            "active": False,
            "active_tier": None,
            "base_price": base_price,
        }

    tier = active_tiers[0]
    discount_meta = frappe.db.get_value(
        "Web Discount",
        tier.parent,
        ["event", "base_price"],
        as_dict=True,
    )
    start_iso = get_datetime(tier.start_datetime).strftime("%Y-%m-%dT%H:%M:%S")
    end_iso = get_datetime(tier.end_datetime).strftime("%Y-%m-%dT%H:%M:%S")

    return {
        "template_id": template_id,
        "active": True,
        "base_price": discount_meta.base_price,
        "active_tier": {
            "event": discount_meta.event,
            "startDate": start_iso,
            "endDate": end_iso,
            "discount_percent": tier.discount_percent,
            "final_price": tier.final_price,
        },
    }