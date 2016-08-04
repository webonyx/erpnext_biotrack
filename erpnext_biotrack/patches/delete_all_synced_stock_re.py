from __future__ import unicode_literals
import frappe

def execute():
	"""Executed by bench execute erpnext_biotrack.patches.delete_all_synced_stock_entries.execute """

	frappe.flags.mute_emails = True
	rows = frappe.get_all('Stock Reconciliation', filters = {"external_transaction_id": ("!=", 0)}, fields=["name", "docstatus"])
	i = 0
	for row in rows:
		i += 1
		print "Deleting " + row['name']
		if row["docstatus"] == 1:
			doc = frappe.get_doc('Stock Reconciliation', row['name'])
			doc.cancel()

		frappe.delete_doc('Stock Reconciliation', row['name'])

		if i % 10 == 0:
			frappe.db.commit()

	frappe.flags.mute_emails = False