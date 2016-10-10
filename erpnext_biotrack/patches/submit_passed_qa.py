from __future__ import unicode_literals
import frappe

def execute():
	"""bench execute erpnext_biotrack.patches.submit_passed_qa.execute"""
	frappe.flags.in_patch = True

	for name in frappe.get_all("Quality Inspection", {"test_result": "Passed", "docstatus": 0}):
		print name
		doc = frappe.get_doc("Quality Inspection", name)
		doc.get_item_specification_details()
		doc.submit()
		frappe.db.commit()

	frappe.flags.in_patch = False
