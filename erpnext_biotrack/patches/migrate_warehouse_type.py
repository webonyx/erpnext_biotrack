from __future__ import unicode_literals

import frappe
from erpnext_biotrack.sources.biotrack.inventory_room import sync as sync_inventory_room
from erpnext_biotrack.sources.biotrack.plant_room import sync as sync_plant_room
from erpnext_biotrack.sources.biotrack.inventory import sync as sync_inventory
from frappe.utils.fixtures import sync_fixtures

def execute():

	sync_fixtures()

	frappe.db.sql("update tabWarehouse set warehouse_type=%(warehouse_type)s where plant_room=1",
				  {"warehouse_type": "Plant Room"})

	frappe.db.sql("update tabWarehouse set warehouse_type=%(warehouse_type)s where plant_room=0 and is_group = 0",
				  {"warehouse_type": "Inventory Room"})

	frappe.db.sql("update tabWarehouse set warehouse_type='' where external_id IS NULL")

	frappe.delete_doc_if_exists("Custom Field", "Warehouse-plant_room")

