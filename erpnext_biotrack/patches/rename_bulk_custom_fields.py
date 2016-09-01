from __future__ import unicode_literals

import frappe
from erpnext_biotrack.utils import rename_custom_field

def execute():

	drop_columns('Warehouse', ['quarentine', 'biotrack_transaction_id',
							   'biotrack_warehouse_transaction_id_original', 'biotrack_warehouse_location_id'])
	drop_columns('Customer', ['license_no', 'ubi', 'biotrack_customer_transaction_id_original'
		, 'biotrack_customer_license_type', 'biotrack_customer_license', 'biotrack_customer_ubi'])

	drop_columns('Stock Entry', ['biotrack_stock_strain', 'biotrack_stock_type', 'biotrack_inventory_id'
		, 'biotrack_inventory_type', 'biotrack_stock_transaction_id_original'])

	frappe.delete_doc('Custom Field', 'Customer-biotrack_customer_license_type')
	frappe.delete_doc('Custom Field', 'Customer-biotrack_customer_license')
	frappe.delete_doc('Custom Field', 'Customer-biotrack_customer_ubi')
	frappe.delete_doc('Custom Field', 'Customer-biotrack_customer_transaction_id_original')

	frappe.delete_doc('Custom Field', 'Warehouse-biotrack_warehouse_location_id')
	frappe.delete_doc('Custom Field', 'Warehouse-biotrack_transaction_id')
	frappe.delete_doc('Custom Field', 'Warehouse-biotrack_warehouse_transaction_id_original')
	frappe.delete_doc('Custom Field', 'Warehouse-biotrack_warehouse')

	frappe.delete_doc('Custom Field', 'Employee-external_transaction_id_original')
	frappe.delete_doc('Custom Field', 'Stock Entry-biotrack_stock_section_break')

	rename_custom_field('Warehouse', 'biotrack_warehouse_sync', 'wa_state_compliance_sync')
	rename_custom_field('Warehouse', 'biotrack_room_id', 'external_id')
	rename_custom_field('Warehouse', 'biotrack_warehouse_transaction_id', 'external_transaction_id')
	rename_custom_field('Warehouse', 'biotrack_warehouse_quarantine', 'quarentine')

	rename_custom_field('Stock Entry', 'biotrack_stock_sync', 'wa_state_compliance_sync')
	rename_custom_field('Stock Entry', 'biotrack_stock_is_plant', 'is_plant')
	rename_custom_field('Stock Entry', 'biotrack_stock_transaction_id', 'external_transaction_id')
	rename_custom_field('Stock Entry', 'biotrack_stock_external_id', 'external_id')

def drop_columns(table, columns):
	rows = frappe.db.sql("desc `tab{}`".format(table))
	columns_in_db = {}
	for row in rows:
		columns_in_db[row[0]] = row

	for column in columns:
		if column in columns_in_db:
			frappe.db.sql("ALTER TABLE `tab{}` DROP `{}`".format(table, column))

	frappe.db.commit()