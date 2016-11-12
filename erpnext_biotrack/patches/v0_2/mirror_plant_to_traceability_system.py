from __future__ import unicode_literals

import frappe

def execute():
	frappe.db.sql("UPDATE tabDocType SET `module` = 'Traceability System' WHERE `name` = 'Plant'")
	frappe.reload_doc('traceability_system', 'doctype', 'plant')
	frappe.db.sql("UPDATE tabPlant SET `title` = `strain`, `item_code` = `source`, `bio_barcode` = `barcode`, `bio_transaction_id` = `transaction_id`, `bio_last_sync` = `last_sync`")
