from __future__ import unicode_literals
import frappe

def execute():
	"""Executed by bench execute erpnext_biotrack.patches.delete_all_synced_stock_entries.execute """
	rows = frappe.get_all('Stock Entry', filters = {"external_transaction_id": ("!=", 0)})
	i = 0
	for row in rows:
		i += 1
		print "Deleting " + row['name']
		frappe.delete_doc('Stock Entry', row['name'])

		if i % 10 == 0:
			frappe.db.commit()
