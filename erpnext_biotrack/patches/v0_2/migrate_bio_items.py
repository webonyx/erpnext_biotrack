from __future__ import unicode_literals

import frappe
# bench --force --site abc run-patch erpnext_biotrack.patches.v0_2.migrate_bio_items
def execute():

	frappe.db.sql("UPDATE tabItem SET `bio_barcode` = `barcode` WHERE `transaction_id` IS NOT NULL")
	frappe.db.sql("UPDATE tabItem SET `bio_remaining_quantity` = `actual_qty`")
	frappe.db.sql("UPDATE tabItem SET `bio_last_sync` = `last_sync`")

	frappe.delete_doc_if_exists("Custom Field", "Item-sub_items")
	frappe.delete_doc_if_exists("Custom Field", "Item-sub_lot_sec")
	frappe.delete_doc_if_exists("Custom Field", "Item-actual_qty")
	frappe.delete_doc_if_exists("Custom Field", "Item-last_sync")
	frappe.delete_doc_if_exists("Custom Field", "Item-external_qty")