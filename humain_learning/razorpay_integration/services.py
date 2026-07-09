import frappe
from frappe.utils import now_datetime

frappe.utils.logger.set_log_level("DEBUG")
logger = frappe.logger("razorpay", with_more_info=True, allow_site=True, file_count=50, max_size=10485760)  # 10MB

def tick_up_coupon(coupon_code):
	coupon_doc = frappe.get_doc("Coupon Code", coupon_code)
	coupon_doc.use_count = frappe.utils.cint(coupon_doc.use_count) + 1
	coupon_doc.save(ignore_permissions=True)

@frappe.whitelist()
def generate_payment_link(payload):
	print(payload)


def expire_coupons():
	coupons = frappe.get_all("Coupon Code", filters={"active": 1,"expiry_timer":1,"expires_at": ["<", now_datetime()]}, pluck='name')

	frappe.db.set_value("Coupon Code", {"name": ["in", coupons]}, "active", 0)
	logger.info(f"Expired Coupons: {coupons}")


def mark_deal_as_won(deal_name,amount_paid):
	deal = frappe.get_doc("CRM Deal", deal_name)
	deal.status = "Won"
	deal.deal_value = amount_paid
	deal.save(ignore_permissions=True)


def create_learners(order):
	pass