from __future__ import unicode_literals

import frappe
# bench --force --site abc run-patch erpnext_biotrack.patches.v0_2.mirror_strain_to_traceability_system
def execute():
	frappe.db.sql("UPDATE tabDocType SET `module` = 'Traceability System' WHERE `name` = 'Strain'")
	frappe.reload_doc('traceability_system', 'doctype', 'strain')

