from __future__ import unicode_literals

import frappe
from erpnext_biotrack.sources.biotrack.inventory import get_biotrack_inventories

def execute():
	frappe.db.sql("update tabWarehouse set warehouse_type=%(warehouse_type)s where plant_room=1",
				  {"warehouse_type": "Plant Room"})

	frappe.db.sql("update tabWarehouse set warehouse_type=%(warehouse_type)s where plant_room=0 and is_group = 0",
				  {"warehouse_type": "Inventory Room"})

	frappe.delete_doc_if_exists("Custom Field", "Warehouse-plant_room")