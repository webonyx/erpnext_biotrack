from __future__ import unicode_literals
import frappe
from erpnext_biotrack.item_utils import delete_item


def execute():
	"""bench execute erpnext_biotrack.patches.delete_all_sample_items.execute"""
	# Disable feed update
	frappe.flags.in_patch = True

	for name in frappe.get_all("Item", {"is_sample": 1}):
		print name
		frappe.db.sql("UPDATE tabItem SET sample = NULL WHERE sample = %(name)s", name)
		frappe.db.sql("DELETE FROM `tabItem Sub Lot` WHERE item_code = %(name)s", name)
		delete_item(name)
		frappe.db.commit()

	frappe.delete_doc_if_exists("Custom Field", "Item-is_sample")
	frappe.delete_doc_if_exists("Custom Field", "Item-sample")
	frappe.flags.in_patch = False
