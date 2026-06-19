import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime

from frappe_whatsapp.frappe_whatsapp.doctype.whatsapp_notification.whatsapp_notification import (
	WhatsAppNotification,
)

WINDOW_MINUTES = 5


class CustomWhatsAppNotification(WhatsAppNotification):
	def get_documents_for_today(self):
		print(f"\n=== Processing Notification: {self.name} ===")
		print(f"Current Time: {now_datetime()}")
		print(f"webinar_cron: {self.flags.get('webinar_cron')}")
		print(f"is_custom_reminder: {self.is_custom_reminder}")

		if self.flags.get("webinar_cron"):
			print("Entered webinar_cron branch")

			if self.custom_reminder_time:
				print(f"Custom reminder time: {self.custom_reminder_time}")

				now = now_datetime()
				fire = get_datetime(f"{now.date()} {self.custom_reminder_time}")

				print(f"Now: {now}")
				print(f"Fire Time: {fire}")
				print(f"Window End: {add_to_date(fire, minutes=WINDOW_MINUTES)}")

				if fire <= now < add_to_date(fire, minutes=WINDOW_MINUTES):
					print("Inside custom reminder window")
					super().get_documents_for_today()
				else:
					print("Outside custom reminder window")

				return

			print("Using relative reminder mode")

			offset = self.days_in_advance

			print(f"doctype_event: {self.doctype_event}")
			print(f"days_in_advance: {self.days_in_advance}")

			if self.doctype_event == "Days After":
				offset = -offset

			print(f"Effective offset: {offset}")
			target = add_to_date(now_datetime(), minutes=offset)
			start = add_to_date(target, seconds=-(WINDOW_MINUTES * 60) // 2)
			end = add_to_date(target, seconds=(WINDOW_MINUTES * 60) // 2)

			print(f"Reference Field: {self.date_changed}")
			print(f"Query Start: {start}")
			print(f"Query End: {end}")

			docs = frappe.get_all(
				self.reference_doctype,
				fields=["name", self.date_changed],
				filters=[
					{self.date_changed: (">=", start)},
					{self.date_changed: ("<", end)},
				],
			)

			print(f"Found {len(docs)} matching documents")

			for d in docs:
				print(f"Matched Doc: {d}")

				try:
					doc = frappe.get_doc(self.reference_doctype, d.name)

					print(
						f"Sending template message to doc={doc.name}"
					)

					self.send_template_message(doc)

					print(
						f"Successfully sent template for {doc.name}"
					)

				except Exception:
					print(f"Failed sending for {d.name}")
					print(frappe.get_traceback())

			return

		if self.is_custom_reminder:
			print(
				"Skipping because custom reminder reached through normal scheduler"
			)
			return

		evening_cutoff = now_datetime().replace(
			hour=18,
			minute=59,
			second=0,
			microsecond=0,
		)

		print(f"Evening cutoff: {evening_cutoff}")

		if now_datetime() < evening_cutoff:
			print("Skipping because before evening cutoff")
			return

		print("Calling original get_documents_for_today()")
		super().get_documents_for_today()


def send_webinar_reminders():
	print("\n========== SEND WEBINAR REMINDERS ==========")
	print(f"Current Time: {now_datetime()}")

	notifications = frappe.get_all(
		"WhatsApp Notification",
		filters={"is_custom_reminder": 1, "disabled": 0},
		pluck="name",
	)

	print(f"Found {len(notifications)} custom notifications")

	for name in notifications:
		print(f"\nProcessing Notification: {name}")

		try:
			notif = frappe.get_doc("WhatsApp Notification", name)

			notif.flags.webinar_cron = True

			notif.get_documents_for_today()

		except Exception:
			print(f"Failed processing notification: {name}")
			print(frappe.get_traceback())

	print("========== END ==========\n")