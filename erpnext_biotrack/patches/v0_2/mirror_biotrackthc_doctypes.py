from __future__ import unicode_literals

import frappe
# bench --force --site abc run-patch erpnext_biotrack.patches.v0_2.mirror_biotrackthc_doctypes
def execute():
	if not frappe.db.exists("Module Def", "BioTrackTHC"):
		doc = frappe.get_doc({
			"doctype": "Module Def",
			"app_name": "erpnext_biotrack",
			"module_name": "BioTrackTHC",
		})
		doc.save(ignore_permissions=True)

	frappe.db.sql("UPDATE tabDocType SET `module` = 'BioTrackTHC' WHERE `name` = 'BioTrack Settings'")
	frappe.db.sql("UPDATE tabDocType SET `module` = 'BioTrackTHC' WHERE `name` = 'BioTrack Log'")
	frappe.db.sql("UPDATE tabDocType SET `module` = 'Traceability System' WHERE `name` = 'Item Sub Lot'")
	frappe.reload_doc('biotrackthc', 'doctype', 'biotrack_settings')
	frappe.reload_doc('biotrackthc', 'doctype', 'biotrack_log')
	frappe.reload_doc('traceability_system', 'doctype', 'item_sub_lot')

	frappe.delete_doc_if_exists("DocType", "Item Conversation Detail")
	frappe.delete_doc_if_exists("DocType", "Item Conversation")
	frappe.delete_doc_if_exists("Module Def", "ERPNext BioTrack")