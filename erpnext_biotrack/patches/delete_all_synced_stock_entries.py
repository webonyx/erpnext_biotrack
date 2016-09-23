from __future__ import unicode_literals
import frappe


def execute():
    """Executed by bench execute erpnext_biotrack.patches.delete_all_synced_stock_entries.execute """

    frappe.flags.mute_emails = True
    # rows = frappe.db.sql()
    i = 0

    for name in frappe.get_all("Stock Entry"):
        doc = frappe.get_doc("Stock Entry", name)
        i += 1
        print "Deleting " + doc.name
        print doc
        if doc.docstatus == 1:
            doc.cancel()

        doc.delete()

        frappe.db.commit()

    frappe.flags.mute_emails = False
