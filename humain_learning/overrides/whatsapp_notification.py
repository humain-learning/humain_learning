import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime

from frappe_whatsapp.frappe_whatsapp.doctype.whatsapp_notification.whatsapp_notification import (
    WhatsAppNotification,
)

WINDOW_MINUTES = 5  # one cron tick; must match the */5 entry in hooks.py


class CustomWhatsAppNotification(WhatsAppNotification):
    def get_documents_for_today(self):
        if self.flags.get("webinar_cron"):
            # fixed clock-time: fire once at custom_reminder_time, then stock day-window
            if self.custom_reminder_time:
                now = now_datetime()
                fire = get_datetime(f"{now.date()} {self.custom_reminder_time}")
                if fire <= now < add_to_date(fire, minutes=WINDOW_MINUTES):
                    super().get_documents_for_today()
                return

            # relative: days_in_advance read in minutes, before/after start_time
            offset = self.days_in_advance
            if self.doctype_event == "Days After":
                offset = -offset
            start = add_to_date(now_datetime(), minutes=offset)
            end = add_to_date(start, minutes=WINDOW_MINUTES)
            for d in frappe.get_all(
                self.reference_doctype,
                fields="name",
                filters=[
                    {self.date_changed: (">=", start)},
                    {self.date_changed: ("<", end)},
                ],
            ):
                doc = frappe.get_doc(self.reference_doctype, d.name)
                self.send_template_message(doc)
            return

        # any other cron reached a custom reminder -> ours to send, skip it here
        if self.is_custom_reminder:
            return

        # unchanged: existing evening gate, then stock day-based behaviour
        if now_datetime() < now_datetime().replace(hour=18, minute=59, second=0, microsecond=0):
            return
        super().get_documents_for_today()


def send_webinar_reminders():
    for name in frappe.get_all(
        "WhatsApp Notification",
        filters={"is_custom_reminder": 1, "disabled": 0},
        pluck="name",
    ):
        notif = frappe.get_doc("WhatsApp Notification", name)
        notif.flags.webinar_cron = True
        notif.get_documents_for_today()
