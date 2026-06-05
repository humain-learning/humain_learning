from frappe_whatsapp.frappe_whatsapp.doctype.whatsapp_notification.whatsapp_notification import WhatsAppNotification
from frappe.utils import now_datetime


class CustomWhatsAppNotification(WhatsAppNotification):

    def get_documents_for_today(self):
        if now_datetime().hour < 11:
            return
        super().get_documents_for_today()