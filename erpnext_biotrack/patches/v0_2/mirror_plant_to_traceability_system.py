from __future__ import unicode_literals

import frappe
# bench --force --site abc run-patch erpnext_biotrack.patches.v0_2.mirror_plant_to_traceability_system
def execute():
	frappe.db.sql("UPDATE tabDocType SET `module` = 'Traceability System' WHERE `name` = 'Plant'")
	frappe.reload_doc('traceability_system', 'doctype', 'plant')
	frappe.db.sql("UPDATE tabPlant SET `title` = `strain` WHERE title = '{strain}' or title IS NULL")
	frappe.db.sql("UPDATE tabPlant SET `naming_series` = 'PLANT-' WHERE naming_series IS NULL")
	frappe.db.sql("UPDATE tabPlant SET `docstatus` = 1 WHERE docstatus = 0")
	frappe.db.sql("UPDATE tabPlant SET `item_code` = `source` WHERE source IS NOT NULL")
	frappe.db.sql("UPDATE tabPlant SET `bio_barcode` = `barcode` WHERE barcode IS NOT NULL")
	frappe.db.sql("UPDATE tabPlant SET `bio_transaction_id` = `transaction_id` WHERE transaction_id IS NOT NULL")
	frappe.db.sql("UPDATE tabPlant SET `bio_last_sync` = `last_sync` WHERE last_sync IS NOT NULL")
	frappe.db.sql("UPDATE tabPlant SET `destroy_scheduled` = `remove_scheduled` WHERE remove_scheduled IS NOT NULL")
	frappe.db.sql("UPDATE tabPlant SET `posting_date` = DATE(`birthdate`) WHERE birthdate IS NOT NULL")
	frappe.db.sql("UPDATE tabPlant SET `posting_time` = TIME(`birthdate`) WHERE birthdate IS NOT NULL")

	frappe.clear_cache()
