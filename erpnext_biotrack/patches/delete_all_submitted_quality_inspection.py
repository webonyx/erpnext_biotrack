from __future__ import unicode_literals
import frappe


def execute():
	"""bench execute erpnext_biotrack.patches.delete_all_submitted_quality_inspection.execute """

	# Disable feed update
	frappe.flags.in_patch = True

	for name in frappe.get_all("Quality Inspection"):
		doc = frappe.get_doc("Quality Inspection", name)
		print "Deleting " + doc.name

		if doc.docstatus == 1:
			doc.cancel()

		doc.delete()

		frappe.db.commit()


	frappe.flags.in_patch = False
