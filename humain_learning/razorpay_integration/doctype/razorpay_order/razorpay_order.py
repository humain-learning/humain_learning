# Copyright (c) 2026, Raghav Kaul and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from ...services import tick_up_coupon,mark_deal_as_won

class RazorpayOrder(Document):
		
	def on_update(self):
		if self.has_value_changed("payment_status") and self.payment_status == "Captured":
			self.post_sale_handler()
			
	def before_save(self):
		if self.status == "Paid" and self.has_value_changed("status"):
			if self.amount_paid == 0:
				self.amount_paid,self.amount_due = self.amount, 0

			elif self.amount_paid > 0:
				self.amount_due = self.amount - self.amount_paid

	def post_sale_handler(self):
		if self.coupon_code:
			tick_up_coupon(self.coupon_code)

		mark_deal_as_won(self.deal,self.amount_paid)
		# create_students(self)
		# From Learner's table, create students and create enrollments.
		# post sale communications