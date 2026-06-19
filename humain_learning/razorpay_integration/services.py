import frappe

def tick_up_coupon(coupon_code):
	coupon_doc = frappe.get_doc("Coupon Code", coupon_code)
	coupon_doc.use_count = frappe.utils.cint(coupon_doc.use_count) + 1
	coupon_doc.save(ignore_permissions=True)