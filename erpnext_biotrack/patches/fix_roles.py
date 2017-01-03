from __future__ import unicode_literals
import frappe

def execute():
	"""bench execute erpnext_biotrack.patches.fix_roles.execute"""
	for doctype in ["Plant", "Plant Entry", "Plant Room", "Strain", "BioTrack Settings", "Traceability Settings"]:
		if frappe.db.exists("DocType", doctype):
			frappe.reload_doctype(doctype, True)

