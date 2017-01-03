from __future__ import unicode_literals

import frappe
def execute():
	frappe.db.sql("UPDATE tabDocType SET `module` = 'Traceability' WHERE `name` IN ('Plant', 'Plant Room', 'Strain')")
	frappe.db.sql("UPDATE `tabDesktop Icon` SET `module_name` = 'Traceability', icon = 'fa fa-leaf' WHERE `module_name` = 'Traceability System'")
	frappe.reload_doc('traceability', 'doctype', 'plant', force=True)
	frappe.reload_doc('traceability', 'doctype', 'strain', force=True)
	frappe.reload_doc('traceability', 'doctype', 'plant_room', force=True)
	frappe.clear_cache()
