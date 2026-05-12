import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_datetime


class WebDiscount(Document):
    def validate(self):
        self._set_final_prices()
        self._validate_row_windows()
        self._validate_no_conflicting_discounts()
        self.event = (self.event or "").strip()
            
    def _validate_row_windows(self):
        for idx, row in enumerate(self.discount_tiers or [], start=1):
            if not row.start_datetime or not row.end_datetime:
                frappe.throw(_("Row {0}: Start and End DateTime are required.").format(idx))

            start = get_datetime(row.start_datetime)
            end = get_datetime(row.end_datetime)

            if end <= start:
                frappe.throw(_("Row {0}: End DateTime must be greater than Start DateTime.").format(idx))
                
                
    def _set_final_prices(self):
        base = flt(self.base_price)
        for row in self.discount_tiers or []:
            percent = flt(row.discount_percent)
            row.final_price = round(base - (base * percent / 100))

    def _validate_no_conflicting_discounts(self):
        # Optional: prevent overlaps inside the same document first
        self._validate_internal_overlaps()

        existing = frappe.db.sql(
            """
            select
                wd.name as web_discount,
                dt.name as tier_name,
                dt.start_datetime,
                dt.end_datetime
            from `tabWeb Discount` wd
            inner join `tabDiscount Tier` dt on dt.parent = wd.name
            where wd.course = %(course)s
              and wd.name != %(current_name)s
              and dt.docstatus < 2
            """,
            {
                "course": self.course,
                "current_name": self.name or "",
            },
            as_dict=True,
        )

        for row in self.discount_tiers or []:
            if not row.start_datetime or not row.end_datetime:
                continue

            s1 = get_datetime(row.start_datetime)
            e1 = get_datetime(row.end_datetime)

            for ex in existing:
                if not ex.start_datetime or not ex.end_datetime:
                    continue

                s2 = get_datetime(ex.start_datetime)
                e2 = get_datetime(ex.end_datetime)

                # Overlap condition: [s1, e1) intersects [s2, e2)
                if s1 < e2 and s2 < e1:
                    frappe.throw(
                        _("Discount period overlaps with {0} ({1} - {2}).")
                        .format(ex.web_discount, ex.start_datetime, ex.end_datetime)
                    )

    def _validate_internal_overlaps(self):
        rows = self.discount_tiers or []
        for i, a in enumerate(rows):
            for b in rows[i + 1:]:
                if not (a.start_datetime and a.end_datetime and b.start_datetime and b.end_datetime):
                    continue

                s1, e1 = get_datetime(a.start_datetime), get_datetime(a.end_datetime)
                s2, e2 = get_datetime(b.start_datetime), get_datetime(b.end_datetime)

                if s1 < e2 and s2 < e1:
                    frappe.throw(_("Two discount tiers in this document have overlapping times."))