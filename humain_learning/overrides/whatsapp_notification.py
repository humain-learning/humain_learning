from frappe_whatsapp.frappe_whatsapp.doctype.whatsapp_notification.whatsapp_notification import WhatsAppNotification
from frappe.utils import now_datetime
import datetime
class CustomWhatsAppNotification(WhatsAppNotification):

    def get_documents_for_today(self):
        if now_datetime() < now_datetime().replace(hour=18, minute=59, second=0, microsecond=0):
            return
        super().get_documents_for_today()